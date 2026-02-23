"""
考勤管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime

from app.database import get_db
from app.api.deps import get_current_user, get_counselor_or_admin
from app.models.user import User
from app.models.student import Student
from app.models.attendance import Attendance, AttendanceStatus
from app.models.course import Course

router = APIRouter()


# ========== Schemas ==========

class AttendanceCreate(BaseModel):
    """创建考勤请求"""
    student_id: int
    course_id: int
    date: str  # YYYY-MM-DD 格式
    status: str  # present, absent, late, leave
    remark: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ['present', 'absent', 'late', 'leave']
        if v not in valid_statuses:
            raise ValueError(f'考勤状态必须是: {", ".join(valid_statuses)}')
        return v

    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式必须为 YYYY-MM-DD')
        return v


class AttendanceUpdate(BaseModel):
    """更新考勤请求"""
    status: Optional[str] = None
    remark: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        valid_statuses = ['present', 'absent', 'late', 'leave']
        if v not in valid_statuses:
            raise ValueError(f'考勤状态必须是: {", ".join(valid_statuses)}')
        return v


class AttendanceResponse(BaseModel):
    """考勤响应"""
    id: int
    student_id: int
    student_no: str
    student_name: str
    class_name: Optional[str] = None
    course_id: int
    course_name: str
    date: str
    status: str
    status_text: str
    remark: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceStats(BaseModel):
    """考勤统计"""
    total: int
    present: int
    absent: int
    late: int
    leave: int
    attendance_rate: float


# ========== 工具函数 ==========

def get_status_text(status: str) -> str:
    """获取状态中文文本"""
    status_map = {
        'present': '正常',
        'absent': '旷课',
        'late': '迟到',
        'leave': '请假'
    }
    return status_map.get(status, status)


# ========== API 端点 ==========

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
    _: User = Depends(get_current_user)
):
    """
    获取考勤列表

    - **page**: 页码
    - **page_size**: 每页数量
    - **student_no**: 学号筛选
    - **student_name**: 学生姓名筛选
    - **course_name**: 课程名称筛选
    - **status**: 考勤状态筛选 (present/absent/late/leave)
    - **start_date**: 开始日期 (YYYY-MM-DD)
    - **end_date**: 结束日期 (YYYY-MM-DD)
    - **class_id**: 班级ID筛选
    """
    query = db.query(Attendance).join(Attendance.student).join(Attendance.course)

    # 按学号筛选
    if student_no:
        query = query.filter(Student.student_no.like(f"%{student_no}%"))

    # 按学生姓名筛选
    if student_name:
        query = query.filter(Student.name.like(f"%{student_name}%"))

    # 按课程名称筛选
    if course_name:
        query = query.filter(Course.course_name.like(f"%{course_name}%"))

    # 按状态筛选
    if status:
        try:
            query = query.filter(Attendance.status == AttendanceStatus(status))
        except ValueError:
            pass

    # 按日期范围筛选
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Attendance.date >= start)
        except ValueError:
            pass

    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Attendance.date <= end)
        except ValueError:
            pass

    # 按班级筛选
    if class_id:
        query = query.filter(Student.class_id == class_id)

    total = query.count()
    attendances = query.order_by(Attendance.date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for a in attendances:
        status_value = a.status.value if isinstance(a.status, AttendanceStatus) else a.status
        items.append({
            "id": a.id,
            "student_id": a.student_id,
            "student_no": a.student.student_no if a.student else "",
            "student_name": a.student.name if a.student else "",
            "class_name": a.student.class_info.name if a.student and a.student.class_info else None,
            "course_id": a.course_id,
            "course_name": a.course.course_name if a.course else "",
            "date": str(a.date),
            "status": status_value,
            "status_text": get_status_text(status_value),
            "remark": a.remark
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/stats", response_model=AttendanceStats, summary="获取考勤统计")
def get_attendance_stats(
    student_id: Optional[int] = None,
    class_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """
    获取考勤统计

    - **student_id**: 学生ID（可选）
    - **class_id**: 班级ID（可选）
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    """
    query = db.query(Attendance)

    # 按学生筛选
    if student_id:
        query = query.filter(Attendance.student_id == student_id)

    # 按班级筛选
    if class_id:
        query = query.join(Attendance.student).filter(Student.class_id == class_id)

    # 按日期范围筛选
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Attendance.date >= start)
        except ValueError:
            pass

    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Attendance.date <= end)
        except ValueError:
            pass

    attendances = query.all()

    total = len(attendances)
    present = sum(1 for a in attendances if a.status == AttendanceStatus.PRESENT)
    absent = sum(1 for a in attendances if a.status == AttendanceStatus.ABSENT)
    late = sum(1 for a in attendances if a.status == AttendanceStatus.LATE)
    leave = sum(1 for a in attendances if a.status == AttendanceStatus.LEAVE)

    # 出勤率 = (出勤 + 迟到 + 请假) / 总数
    attendance_rate = round(((present + late + leave) / total * 100), 2) if total > 0 else 100

    return AttendanceStats(
        total=total,
        present=present,
        absent=absent,
        late=late,
        leave=leave,
        attendance_rate=attendance_rate
    )


@router.get("/courses", response_model=dict, summary="获取课程列表（用于下拉框）")
def get_courses_for_select(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取课程列表，用于下拉选择"""
    courses = db.query(Course).order_by(Course.course_code).all()

    items = []
    for c in courses:
        items.append({
            "id": c.id,
            "course_code": c.course_code,
            "course_name": c.course_name,
            "semester": c.semester
        })

    return {"items": items}


@router.post("", response_model=dict, summary="创建考勤记录")
def create_attendance(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_counselor_or_admin)
):
    """创建考勤记录"""
    # 检查学生是否存在
    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    # 检查课程是否存在
    course = db.query(Course).filter(Course.id == data.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )

    # 解析日期
    try:
        record_date = datetime.strptime(data.date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="日期格式错误"
        )

    # 检查是否已存在相同记录
    existing = db.query(Attendance).filter(
        Attendance.student_id == data.student_id,
        Attendance.course_id == data.course_id,
        Attendance.date == record_date
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该学生此课程当天已有考勤记录"
        )

    # 创建考勤记录
    attendance = Attendance(
        student_id=data.student_id,
        course_id=data.course_id,
        date=record_date,
        status=AttendanceStatus(data.status),
        remark=data.remark
    )

    db.add(attendance)
    db.commit()
    db.refresh(attendance)

    return {
        "message": "考勤记录创建成功",
        "id": attendance.id
    }


@router.put("/{attendance_id}", response_model=dict, summary="更新考勤记录")
def update_attendance(
    attendance_id: int,
    data: AttendanceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_counselor_or_admin)
):
    """更新考勤记录"""
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="考勤记录不存在"
        )

    # 更新状态
    if data.status:
        attendance.status = AttendanceStatus(data.status)

    # 更新备注
    if data.remark is not None:
        attendance.remark = data.remark

    db.commit()

    return {"message": "考勤记录更新成功"}


@router.delete("/{attendance_id}", response_model=dict, summary="删除考勤记录")
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_counselor_or_admin)
):
    """删除考勤记录"""
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="考勤记录不存在"
        )

    db.delete(attendance)
    db.commit()

    return {"message": "考勤记录删除成功"}


@router.post("/batch", response_model=dict, summary="批量录入考勤")
def batch_create_attendances(
    data: List[AttendanceCreate],
    db: Session = Depends(get_db),
    _: User = Depends(get_counselor_or_admin)
):
    """批量录入考勤"""
    success_count = 0
    failed_count = 0
    errors = []

    for i, item in enumerate(data):
        try:
            # 检查学生是否存在
            student = db.query(Student).filter(Student.id == item.student_id).first()
            if not student:
                errors.append(f"第{i+1}条: 学生ID {item.student_id} 不存在")
                failed_count += 1
                continue

            # 检查课程是否存在
            course = db.query(Course).filter(Course.id == item.course_id).first()
            if not course:
                errors.append(f"第{i+1}条: 课程ID {item.course_id} 不存在")
                failed_count += 1
                continue

            # 解析日期
            record_date = datetime.strptime(item.date, '%Y-%m-%d').date()

            # 检查是否已存在
            existing = db.query(Attendance).filter(
                Attendance.student_id == item.student_id,
                Attendance.course_id == item.course_id,
                Attendance.date == record_date
            ).first()

            if existing:
                # 更新已有记录
                existing.status = AttendanceStatus(item.status)
                if item.remark:
                    existing.remark = item.remark
            else:
                # 创建新记录
                attendance = Attendance(
                    student_id=item.student_id,
                    course_id=item.course_id,
                    date=record_date,
                    status=AttendanceStatus(item.status),
                    remark=item.remark
                )
                db.add(attendance)

            success_count += 1
        except Exception as e:
            errors.append(f"第{i+1}条: {str(e)}")
            failed_count += 1

    db.commit()

    return {
        "message": f"批量录入完成: 成功 {success_count} 条, 失败 {failed_count} 条",
        "success": success_count,
        "failed": failed_count,
        "errors": errors
    }
