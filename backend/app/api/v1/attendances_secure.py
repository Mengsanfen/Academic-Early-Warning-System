"""
Attendance management APIs with counselor class scoping.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.api.deps import (
    apply_class_filter,
    check_class_access,
    check_student_access,
    get_counselor_or_admin,
)
from app.database import get_db
from app.models.attendance import Attendance, AttendanceStatus
from app.models.course import Course
from app.models.student import Student
from app.models.user import User, UserRole


router = APIRouter()


class AttendanceCreate(BaseModel):
    student_id: int
    course_id: int
    date: str
    status: str
    remark: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"present", "absent", "late", "leave"}:
            raise ValueError("考勤状态必须是 present/absent/late/leave")
        return value

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%d")
        return value


class AttendanceUpdate(BaseModel):
    status: Optional[str] = None
    remark: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in {"present", "absent", "late", "leave"}:
            raise ValueError("考勤状态必须是 present/absent/late/leave")
        return value


def _get_status_text(status_value: str) -> str:
    return {
        "present": "正常",
        "absent": "旷课",
        "late": "迟到",
        "leave": "请假",
    }.get(status_value, status_value)


def _ensure_class_access(current_user: User, class_id: int) -> None:
    if current_user.role == UserRole.COUNSELOR and not check_class_access(current_user, class_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限访问该班级的数据",
        )


def _ensure_student_access(current_user: User, student_id: int, db: Session) -> None:
    if not check_student_access(current_user, student_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限操作该学生的数据",
        )


def _ensure_course_access(current_user: User, course: Course) -> None:
    if current_user.role != UserRole.COUNSELOR:
        return
    if not course.class_id or not check_class_access(current_user, course.class_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限操作该课程的数据",
        )


def _serialize_attendance(attendance: Attendance) -> dict:
    status_value = attendance.status.value if isinstance(attendance.status, AttendanceStatus) else str(attendance.status)
    return {
        "id": attendance.id,
        "student_id": attendance.student_id,
        "student_no": attendance.student.student_no if attendance.student else "",
        "student_name": attendance.student.name if attendance.student else "",
        "class_name": attendance.student.class_info.name if attendance.student and attendance.student.class_info else None,
        "course_id": attendance.course_id,
        "course_name": attendance.course.course_name if attendance.course else "",
        "date": str(attendance.date),
        "status": status_value,
        "status_text": _get_status_text(status_value),
        "remark": attendance.remark,
    }


@router.get("", response_model=dict, summary="获取考勤列表")
def get_attendances(
    page: int = 1,
    page_size: int = 20,
    student_no: Optional[str] = None,
    student_name: Optional[str] = None,
    course_name: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    class_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    query = db.query(Attendance).join(Attendance.student).join(Attendance.course)
    query = apply_class_filter(query, current_user, Student.class_id)

    if student_no:
        query = query.filter(Student.student_no.like(f"%{student_no}%"))
    if student_name:
        query = query.filter(Student.name.like(f"%{student_name}%"))
    if course_name:
        query = query.filter(Course.course_name.like(f"%{course_name}%"))
    if status:
        try:
            query = query.filter(Attendance.status == AttendanceStatus(status))
        except ValueError:
            pass
    if start_date:
        query = query.filter(Attendance.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(Attendance.date <= datetime.strptime(end_date, "%Y-%m-%d").date())
    if class_id is not None:
        _ensure_class_access(current_user, class_id)
        query = query.filter(Student.class_id == class_id)

    total = query.count()
    attendances = (
        query.order_by(Attendance.date.desc(), Attendance.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [_serialize_attendance(item) for item in attendances],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/stats", response_model=dict, summary="获取考勤统计")
def get_attendance_stats(
    student_id: Optional[int] = None,
    class_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    query = db.query(Attendance).join(Attendance.student)
    query = apply_class_filter(query, current_user, Student.class_id)

    if student_id is not None:
        _ensure_student_access(current_user, student_id, db)
        query = query.filter(Attendance.student_id == student_id)
    if class_id is not None:
        _ensure_class_access(current_user, class_id)
        query = query.filter(Student.class_id == class_id)
    if start_date:
        query = query.filter(Attendance.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(Attendance.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    attendances = query.all()
    total = len(attendances)
    present = sum(1 for item in attendances if item.status == AttendanceStatus.PRESENT)
    absent = sum(1 for item in attendances if item.status == AttendanceStatus.ABSENT)
    late = sum(1 for item in attendances if item.status == AttendanceStatus.LATE)
    leave = sum(1 for item in attendances if item.status == AttendanceStatus.LEAVE)
    attendance_rate = round(((present + late + leave) / total * 100), 2) if total else 100

    return {
        "total": total,
        "present": present,
        "absent": absent,
        "late": late,
        "leave": leave,
        "attendance_rate": attendance_rate,
    }


@router.get("/courses", response_model=dict, summary="获取课程列表")
def get_courses_for_select(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    query = db.query(Course)
    query = apply_class_filter(query, current_user, Course.class_id)
    courses = query.order_by(Course.course_code).all()
    return {
        "items": [
            {
                "id": course.id,
                "course_code": course.course_code,
                "course_name": course.course_name,
                "semester": course.semester,
            }
            for course in courses
        ]
    }


@router.post("", response_model=dict, summary="创建考勤记录")
def create_attendance(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")
    _ensure_student_access(current_user, student.id, db)

    course = db.query(Course).filter(Course.id == data.course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    _ensure_course_access(current_user, course)

    record_date = datetime.strptime(data.date, "%Y-%m-%d").date()
    existing = db.query(Attendance).filter(
        Attendance.student_id == data.student_id,
        Attendance.course_id == data.course_id,
        Attendance.date == record_date,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该考勤记录已存在")

    attendance = Attendance(
        student_id=data.student_id,
        course_id=data.course_id,
        date=record_date,
        status=AttendanceStatus(data.status),
        remark=data.remark,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return {"message": "考勤记录创建成功", "id": attendance.id}


@router.put("/{attendance_id}", response_model=dict, summary="更新考勤记录")
def update_attendance(
    attendance_id: int,
    data: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考勤记录不存在")

    _ensure_student_access(current_user, attendance.student_id, db)
    if data.status is not None:
        attendance.status = AttendanceStatus(data.status)
    if data.remark is not None:
        attendance.remark = data.remark

    db.commit()
    return {"message": "考勤记录更新成功"}


@router.delete("/{attendance_id}", response_model=dict, summary="删除考勤记录")
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考勤记录不存在")

    _ensure_student_access(current_user, attendance.student_id, db)
    db.delete(attendance)
    db.commit()
    return {"message": "考勤记录删除成功"}


@router.post("/batch", response_model=dict, summary="批量录入考勤")
def batch_create_attendances(
    data: list[AttendanceCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    success_count = 0
    failed_count = 0
    errors: list[str] = []

    for index, item in enumerate(data, start=1):
        try:
            student = db.query(Student).filter(Student.id == item.student_id).first()
            if not student:
                raise ValueError(f"学生ID {item.student_id} 不存在")
            _ensure_student_access(current_user, student.id, db)

            course = db.query(Course).filter(Course.id == item.course_id).first()
            if not course:
                raise ValueError(f"课程ID {item.course_id} 不存在")
            _ensure_course_access(current_user, course)

            record_date = datetime.strptime(item.date, "%Y-%m-%d").date()
            existing = db.query(Attendance).filter(
                Attendance.student_id == item.student_id,
                Attendance.course_id == item.course_id,
                Attendance.date == record_date,
            ).first()

            if existing:
                existing.status = AttendanceStatus(item.status)
                existing.remark = item.remark
            else:
                db.add(
                    Attendance(
                        student_id=item.student_id,
                        course_id=item.course_id,
                        date=record_date,
                        status=AttendanceStatus(item.status),
                        remark=item.remark,
                    )
                )
            success_count += 1
        except Exception as exc:
            failed_count += 1
            errors.append(f"第 {index} 条: {exc}")

    db.commit()
    return {
        "message": f"批量录入完成: 成功 {success_count} 条, 失败 {failed_count} 条",
        "success": success_count,
        "failed": failed_count,
        "errors": errors,
    }
