"""课程管理 API。"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import (
    apply_class_filter,
    check_class_access,
    get_admin_user,
    get_counselor_or_admin,
)
from app.database import get_db
from app.models.course import Course, CourseType
from app.models.score import Score
from app.models.student import Class
from app.models.user import User

router = APIRouter()


class CourseCreate(BaseModel):
    course_code: str
    course_name: str
    credit: float
    semester: str
    class_id: Optional[int] = None
    teacher_name: Optional[str] = None
    course_type: str = "required"


class CourseUpdate(BaseModel):
    course_name: Optional[str] = None
    credit: Optional[float] = None
    semester: Optional[str] = None
    class_id: Optional[int] = None
    teacher_name: Optional[str] = None
    course_type: Optional[str] = None


class CourseBatchUpdateType(BaseModel):
    course_ids: List[int]
    course_type: str


COURSE_TYPE_OPTIONS = [
    {"value": CourseType.REQUIRED.value, "label": "必修课", "description": "培养方案要求必须修读的课程"},
    {"value": CourseType.ELECTIVE.value, "label": "选修课", "description": "学生按要求自主选择修读的课程"},
    {"value": CourseType.PUBLIC.value, "label": "公共课", "description": "通识类或公共基础课程"},
    {"value": CourseType.PROFESSIONAL.value, "label": "专业课", "description": "专业核心及方向课程"},
    {"value": CourseType.PRACTICE.value, "label": "实践课", "description": "实验、实训、实习、课程设计等实践教学课程"},
]


COURSE_TYPE_NAME_MAP = {item["value"]: item["label"] for item in COURSE_TYPE_OPTIONS}


def _parse_course_type(course_type: Optional[str], *, required: bool = False) -> Optional[CourseType]:
    if course_type in (None, ""):
        if required:
            return CourseType.REQUIRED
        return None
    try:
        return CourseType(course_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的课程类型",
        ) from exc


def _serialize_course(course: Course) -> dict:
    course_type = course.course_type.value if course.course_type else CourseType.REQUIRED.value
    class_info = course.class_info
    return {
        "id": course.id,
        "course_code": course.course_code,
        "course_name": course.course_name,
        "credit": float(course.credit) if course.credit is not None else 0,
        "semester": course.semester,
        "class_id": course.class_id,
        "class_name": class_info.name if class_info else None,
        "grade": class_info.grade if class_info else None,
        "department_name": class_info.department.name if class_info and class_info.department else None,
        "teacher_name": course.teacher_name,
        "course_type": course_type,
        "course_type_name": COURSE_TYPE_NAME_MAP.get(course_type, course_type),
    }


@router.get("", response_model=dict, summary="获取课程列表")
def get_courses(
    page: int = 1,
    page_size: int = 20,
    course_name: Optional[str] = None,
    semester: Optional[str] = None,
    course_type: Optional[str] = None,
    class_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    query = db.query(Course).options(joinedload(Course.class_info).joinedload(Class.department))
    query = apply_class_filter(query, current_user, Course.class_id)

    if course_name:
        query = query.filter(Course.course_name.like(f"%{course_name}%"))
    if semester:
        query = query.filter(Course.semester == semester)
    if class_id:
        query = query.filter(Course.class_id == class_id)
    parsed_course_type = _parse_course_type(course_type)
    if parsed_course_type:
        query = query.filter(Course.course_type == parsed_course_type)

    total = query.count()
    items = (
        query.order_by(Course.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [_serialize_course(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/all", response_model=dict, summary="获取全部课程")
def get_all_courses(
    semester: Optional[str] = None,
    course_type: Optional[str] = None,
    class_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    query = db.query(Course).options(joinedload(Course.class_info).joinedload(Class.department))
    query = apply_class_filter(query, current_user, Course.class_id)

    if semester:
        query = query.filter(Course.semester == semester)
    if class_id:
        query = query.filter(Course.class_id == class_id)
    parsed_course_type = _parse_course_type(course_type)
    if parsed_course_type:
        query = query.filter(Course.course_type == parsed_course_type)

    items = query.order_by(Course.course_code.asc(), Course.id.asc()).all()
    return {"items": [_serialize_course(item) for item in items]}


@router.get("/semesters", response_model=dict, summary="获取学期列表")
def get_semesters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    query = db.query(Course.semester).distinct()
    query = apply_class_filter(query, current_user, Course.class_id)
    semesters = query.order_by(Course.semester.desc()).all()
    return {"items": [row[0] for row in semesters if row[0]]}


@router.get("/types", response_model=dict, summary="获取课程类型列表")
def get_course_types():
    return {"items": COURSE_TYPE_OPTIONS}


@router.get("/statistics", response_model=dict, summary="获取课程统计")
def get_course_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    by_type = (
        db.query(Course.course_type, func.count(Course.id).label("count"))
        .group_by(Course.course_type)
        .all()
    )
    by_semester = (
        db.query(Course.semester, func.count(Course.id).label("count"))
        .group_by(Course.semester)
        .order_by(Course.semester.desc())
        .limit(10)
        .all()
    )
    return {
        "by_type": [
            {
                "type": row[0].value if row[0] else "unknown",
                "type_name": COURSE_TYPE_NAME_MAP.get(row[0].value if row[0] else "unknown", "未知类型"),
                "count": row[1],
            }
            for row in by_type
        ],
        "by_semester": [{"semester": row[0], "count": row[1]} for row in by_semester],
        "total": db.query(Course).count(),
    }


@router.get("/{course_id}", response_model=dict, summary="获取课程详情")
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    course = (
        db.query(Course)
        .options(joinedload(Course.class_info).joinedload(Class.department))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    if course.class_id is not None and not check_class_access(current_user, course.class_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该课程")
    return _serialize_course(course)


@router.post("", response_model=dict, summary="创建课程")
def create_course(
    data: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    _ = current_user
    existing = db.query(Course).filter(Course.course_code == data.course_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="课程代码已存在")

    course = Course(
        course_code=data.course_code,
        course_name=data.course_name,
        credit=data.credit,
        semester=data.semester,
        class_id=data.class_id,
        teacher_name=data.teacher_name,
        course_type=_parse_course_type(data.course_type, required=True),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {"message": "课程创建成功", "id": course.id}


@router.put("/{course_id}", response_model=dict, summary="更新课程")
def update_course(
    course_id: int,
    data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    _ = current_user
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")

    payload = data.model_dump(exclude_unset=True)
    if "course_type" in payload:
        payload["course_type"] = _parse_course_type(payload["course_type"], required=True)

    for key, value in payload.items():
        setattr(course, key, value)

    db.commit()
    return {"message": "课程更新成功"}


@router.put("/batch/type", response_model=dict, summary="批量修改课程类型")
def batch_update_course_type(
    data: CourseBatchUpdateType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    _ = current_user
    parsed_course_type = _parse_course_type(data.course_type, required=True)
    updated = (
        db.query(Course)
        .filter(Course.id.in_(data.course_ids))
        .update({"course_type": parsed_course_type}, synchronize_session=False)
    )
    db.commit()
    return {"message": f"成功更新 {updated} 门课程的类型", "updated": updated}


@router.delete("/{course_id}", response_model=dict, summary="删除课程")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    _ = current_user
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")

    score_count = db.query(Score).filter(Score.course_id == course_id).count()
    if score_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该课程存在 {score_count} 条成绩记录，无法删除",
        )

    db.delete(course)
    db.commit()
    return {"message": "课程删除成功"}

