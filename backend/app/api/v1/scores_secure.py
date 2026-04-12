"""
Score management APIs with counselor class scoping.
"""
from __future__ import annotations

from decimal import Decimal
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
from app.models.course import Course
from app.models.score import Score
from app.models.student import Student
from app.models.user import User, UserRole


router = APIRouter()


class ScoreCreate(BaseModel):
    student_id: int
    course_id: int
    score: float
    semester: str
    exam_type: Optional[str] = "期末"

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("成绩必须在 0-100 之间")
        return value


class ScoreUpdate(BaseModel):
    score: float
    exam_type: Optional[str] = None

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("成绩必须在 0-100 之间")
        return value


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


def _serialize_score(score: Score) -> dict:
    return {
        "id": score.id,
        "student_id": score.student_id,
        "student_no": score.student.student_no if score.student else "",
        "student_name": score.student.name if score.student else "",
        "class_name": score.student.class_info.name if score.student and score.student.class_info else None,
        "course_id": score.course_id,
        "course_code": score.course.course_code if score.course else "",
        "course_name": score.course.course_name if score.course else "",
        "credit": float(score.course.credit) if score.course and score.course.credit is not None else 0,
        "score": float(score.score),
        "semester": score.semester,
        "exam_type": score.exam_type,
        "is_passed": score.is_passed,
    }


@router.get("", response_model=dict, summary="获取成绩列表")
def get_scores(
    page: int = 1,
    page_size: int = 20,
    student_no: Optional[str] = None,
    student_name: Optional[str] = None,
    course_name: Optional[str] = None,
    semester: Optional[str] = None,
    is_passed: Optional[bool] = None,
    class_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    query = db.query(Score).join(Score.student).join(Score.course)
    query = apply_class_filter(query, current_user, Student.class_id)

    if student_no:
        query = query.filter(Student.student_no.like(f"%{student_no}%"))
    if student_name:
        query = query.filter(Student.name.like(f"%{student_name}%"))
    if course_name:
        query = query.filter(Course.course_name.like(f"%{course_name}%"))
    if semester:
        query = query.filter(Score.semester == semester)
    if is_passed is not None:
        query = query.filter(Score.score >= 60 if is_passed else Score.score < 60)
    if class_id is not None:
        _ensure_class_access(current_user, class_id)
        query = query.filter(Student.class_id == class_id)

    total = query.count()
    scores = (
        query.order_by(Score.created_at.desc(), Score.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_serialize_score(score) for score in scores],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/courses", response_model=dict, summary="获取课程列表")
def get_courses_for_select(
    semester: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    query = db.query(Course)
    query = apply_class_filter(query, current_user, Course.class_id)

    if semester:
        query = query.filter(Course.semester == semester)

    courses = query.order_by(Course.course_code).all()
    return {
        "items": [
            {
                "id": course.id,
                "course_code": course.course_code,
                "course_name": course.course_name,
                "credit": float(course.credit),
                "semester": course.semester,
            }
            for course in courses
        ]
    }


@router.get("/semesters", response_model=dict, summary="获取学期列表")
def get_semesters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    query = db.query(Score.semester).join(Score.student)
    query = apply_class_filter(query, current_user, Student.class_id)
    semesters = query.distinct().order_by(Score.semester.desc()).all()
    return {"items": [item[0] for item in semesters]}


@router.post("", response_model=dict, summary="创建成绩记录")
def create_score(
    data: ScoreCreate,
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

    if course.class_id and student.class_id and course.class_id != student.class_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="课程与学生班级不匹配")

    existing = db.query(Score).filter(
        Score.student_id == data.student_id,
        Score.course_id == data.course_id,
        Score.semester == data.semester,
        Score.exam_type == data.exam_type,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该成绩记录已存在")

    score = Score(
        student_id=data.student_id,
        course_id=data.course_id,
        score=Decimal(str(data.score)),
        semester=data.semester,
        exam_type=data.exam_type,
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return {"message": "成绩录入成功", "id": score.id}


@router.put("/{score_id}", response_model=dict, summary="更新成绩记录")
def update_score(
    score_id: int,
    data: ScoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成绩记录不存在")

    _ensure_student_access(current_user, score.student_id, db)
    score.score = Decimal(str(data.score))
    if data.exam_type is not None:
        score.exam_type = data.exam_type

    db.commit()
    return {"message": "成绩更新成功"}


@router.delete("/{score_id}", response_model=dict, summary="删除成绩记录")
def delete_score(
    score_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成绩记录不存在")

    _ensure_student_access(current_user, score.student_id, db)
    db.delete(score)
    db.commit()
    return {"message": "成绩删除成功"}


@router.post("/batch", response_model=dict, summary="批量录入成绩")
def batch_create_scores(
    data: list[ScoreCreate],
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

            if course.class_id and student.class_id and course.class_id != student.class_id:
                raise ValueError("课程与学生班级不匹配")

            existing = db.query(Score).filter(
                Score.student_id == item.student_id,
                Score.course_id == item.course_id,
                Score.semester == item.semester,
                Score.exam_type == item.exam_type,
            ).first()

            if existing:
                existing.score = Decimal(str(item.score))
            else:
                db.add(
                    Score(
                        student_id=item.student_id,
                        course_id=item.course_id,
                        score=Decimal(str(item.score)),
                        semester=item.semester,
                        exam_type=item.exam_type,
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
