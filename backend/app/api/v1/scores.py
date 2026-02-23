"""
成绩管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, field_validator
from typing import Optional, List
from decimal import Decimal

from app.database import get_db
from app.api.deps import get_current_user, get_counselor_or_admin
from app.models.user import User
from app.models.student import Student
from app.models.score import Score
from app.models.course import Course

router = APIRouter()


# ========== Schemas ==========

class ScoreCreate(BaseModel):
    """创建成绩请求"""
    student_id: int
    course_id: int
    score: float
    semester: str
    exam_type: Optional[str] = "期末"

    @field_validator('score')
    @classmethod
    def validate_score(cls, v):
        if v < 0 or v > 100:
            raise ValueError('成绩必须在0-100之间')
        return v


class ScoreUpdate(BaseModel):
    """更新成绩请求"""
    score: float
    exam_type: Optional[str] = None

    @field_validator('score')
    @classmethod
    def validate_score(cls, v):
        if v < 0 or v > 100:
            raise ValueError('成绩必须在0-100之间')
        return v


class ScoreResponse(BaseModel):
    """成绩响应"""
    id: int
    student_id: int
    student_no: str
    student_name: str
    class_name: Optional[str] = None
    course_id: int
    course_code: str
    course_name: str
    credit: float
    score: float
    semester: str
    exam_type: Optional[str] = None
    is_passed: bool

    class Config:
        from_attributes = True


class CourseOption(BaseModel):
    """课程选项（用于下拉框）"""
    id: int
    course_code: str
    course_name: str
    credit: float
    semester: str


# ========== API 端点 ==========

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
    _: User = Depends(get_current_user)
):
    """
    获取成绩列表

    - **page**: 页码
    - **page_size**: 每页数量
    - **student_no**: 学号筛选
    - **student_name**: 学生姓名筛选
    - **course_name**: 课程名称筛选
    - **semester**: 学期筛选
    - **is_passed**: 是否及格筛选
    - **class_id**: 班级ID筛选
    """
    query = db.query(Score).join(Score.student).join(Score.course)

    # 按学号筛选
    if student_no:
        query = query.filter(Student.student_no.like(f"%{student_no}%"))

    # 按学生姓名筛选
    if student_name:
        query = query.filter(Student.name.like(f"%{student_name}%"))

    # 按课程名称筛选
    if course_name:
        query = query.filter(Course.course_name.like(f"%{course_name}%"))

    # 按学期筛选
    if semester:
        query = query.filter(Score.semester == semester)

    # 按及格状态筛选
    if is_passed is not None:
        if is_passed:
            query = query.filter(Score.score >= 60)
        else:
            query = query.filter(Score.score < 60)

    # 按班级筛选
    if class_id:
        query = query.filter(Student.class_id == class_id)

    total = query.count()
    scores = query.order_by(Score.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for s in scores:
        items.append({
            "id": s.id,
            "student_id": s.student_id,
            "student_no": s.student.student_no if s.student else "",
            "student_name": s.student.name if s.student else "",
            "class_name": s.student.class_info.name if s.student and s.student.class_info else None,
            "course_id": s.course_id,
            "course_code": s.course.course_code if s.course else "",
            "course_name": s.course.course_name if s.course else "",
            "credit": float(s.course.credit) if s.course else 0,
            "score": float(s.score),
            "semester": s.semester,
            "exam_type": s.exam_type,
            "is_passed": s.is_passed
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/courses", response_model=dict, summary="获取课程列表（用于下拉框）")
def get_courses_for_select(
    semester: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取课程列表，用于下拉选择"""
    query = db.query(Course)

    if semester:
        query = query.filter(Course.semester == semester)

    courses = query.order_by(Course.course_code).all()

    items = []
    for c in courses:
        items.append({
            "id": c.id,
            "course_code": c.course_code,
            "course_name": c.course_name,
            "credit": float(c.credit),
            "semester": c.semester
        })

    return {"items": items}


@router.get("/semesters", response_model=dict, summary="获取学期列表")
def get_semesters(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取所有学期列表"""
    semesters = db.query(Score.semester).distinct().order_by(Score.semester.desc()).all()
    return {"items": [s[0] for s in semesters]}


@router.post("", response_model=dict, summary="创建成绩记录")
def create_score(
    data: ScoreCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_counselor_or_admin)
):
    """创建成绩记录"""
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

    # 检查是否已存在相同记录
    existing = db.query(Score).filter(
        Score.student_id == data.student_id,
        Score.course_id == data.course_id,
        Score.semester == data.semester,
        Score.exam_type == data.exam_type
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该学生此课程成绩记录已存在"
        )

    # 创建成绩记录
    score = Score(
        student_id=data.student_id,
        course_id=data.course_id,
        score=Decimal(str(data.score)),
        semester=data.semester,
        exam_type=data.exam_type
    )

    db.add(score)
    db.commit()
    db.refresh(score)

    return {
        "message": "成绩录入成功",
        "id": score.id
    }


@router.put("/{score_id}", response_model=dict, summary="更新成绩记录")
def update_score(
    score_id: int,
    data: ScoreUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_counselor_or_admin)
):
    """更新成绩记录"""
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="成绩记录不存在"
        )

    # 更新成绩
    score.score = Decimal(str(data.score))

    if data.exam_type:
        score.exam_type = data.exam_type

    db.commit()

    return {"message": "成绩更新成功"}


@router.delete("/{score_id}", response_model=dict, summary="删除成绩记录")
def delete_score(
    score_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_counselor_or_admin)
):
    """删除成绩记录"""
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="成绩记录不存在"
        )

    db.delete(score)
    db.commit()

    return {"message": "成绩删除成功"}


@router.post("/batch", response_model=dict, summary="批量录入成绩")
def batch_create_scores(
    data: List[ScoreCreate],
    db: Session = Depends(get_db),
    _: User = Depends(get_counselor_or_admin)
):
    """批量录入成绩"""
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

            # 检查是否已存在
            existing = db.query(Score).filter(
                Score.student_id == item.student_id,
                Score.course_id == item.course_id,
                Score.semester == item.semester,
                Score.exam_type == item.exam_type
            ).first()

            if existing:
                # 更新已有记录
                existing.score = Decimal(str(item.score))
            else:
                # 创建新记录
                score = Score(
                    student_id=item.student_id,
                    course_id=item.course_id,
                    score=Decimal(str(item.score)),
                    semester=item.semester,
                    exam_type=item.exam_type
                )
                db.add(score)

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
