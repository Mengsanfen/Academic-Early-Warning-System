"""
学生管理 API

包含基于用户角色的数据权限过滤
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from app.database import get_db
from app.api.deps import (
    get_current_user,
    get_counselor_or_admin,
    apply_class_filter,
    check_student_access,
    get_accessible_class_ids
)
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.student import Class


logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Schemas ==========

class StudentCreate(BaseModel):
    """创建学生"""
    student_no: str
    name: str
    gender: str = "男"
    class_id: int
    grade: int
    phone: Optional[str] = None
    email: Optional[str] = None
    id_card: Optional[str] = None
    address: Optional[str] = None


class StudentUpdate(BaseModel):
    """更新学生"""
    name: Optional[str] = None
    gender: Optional[str] = None
    class_id: Optional[int] = None
    grade: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    id_card: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class StudentResponse(BaseModel):
    """学生响应"""
    id: int
    student_no: str
    name: str
    gender: str
    class_id: int
    class_name: Optional[str] = None
    grade: int
    phone: Optional[str]
    email: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ========== API 端点 ==========

@router.get("/list/classes", summary="获取班级列表", response_model=List[dict])
def get_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """
    获取当前用户可访问的班级列表

    返回:
    - admin: 所有班级
    - counselor: 其管理的班级
    - student: 自己所在的班级
    """
    class_ids = get_accessible_class_ids(current_user)

    if class_ids == []:
        # 无权限，返回空数组
        return []

    query = db.query(Class)

    if class_ids is not None:
        # 有限制的班级ID列表
        query = query.filter(Class.id.in_(class_ids))
    # else: None 表示无限制（admin），查询所有

    classes = query.order_by(Class.id.desc()).all()

    return [
        {
            "id": c.id,
            "name": c.name,
            "grade": c.grade
        }
        for c in classes
    ]


@router.get("/accessible-classes", summary="获取可访问的班级列表")
def get_accessible_classes(
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户可访问的班级列表

    返回:
    - admin: 所有班级
    - counselor: 其管理的班级
    - student: 自己所在的班级
    """
    class_ids = get_accessible_class_ids(current_user)

    if class_ids == []:
        # 无权限
        return {"classes": []}

    query = db.query(Class).options(joinedload(Class.department))

    if class_ids is not None:
        # 有限制的班级ID列表
        query = query.filter(Class.id.in_(class_ids))

    if department_id:
        query = query.filter(Class.department_id == department_id)

    classes = query.all()

    return {
        "classes": [
            {
                "id": c.id,
                "name": c.name,
                "grade": c.grade,
                "department_id": c.department_id,
                "department_name": c.department.name if c.department else None,
                "student_count": len(c.students) if c.students else 0
            }
            for c in classes
        ]
    }


@router.get("", response_model=dict, summary="获取学生列表")
def get_students(
    page: int = 1,
    page_size: int = 20,
    class_id: Optional[int] = None,
    name: Optional[str] = None,
    student_no: Optional[str] = None,
    grade: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取学生列表

    权限控制：
    - admin: 可以查看所有学生
    - counselor: 只能查看其管理班级的学生
    - student: 只能查看自己的信息
    """
    # 基础查询
    query = db.query(Student).join(Class, isouter=True)

    # ========== 核心权限过滤 ==========
    # 根据用户角色应用班级过滤
    query = apply_class_filter(query, current_user, Student.class_id)

    # 如果是学生角色，只能查看自己
    if current_user.role == UserRole.STUDENT:
        if not current_user.student:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
        query = query.filter(Student.id == current_user.student.id)

    # ========== 业务过滤条件 ==========
    # 班级过滤（需要检查权限）
    if class_id:
        # 检查用户是否有权限访问该班级
        if current_user.role == UserRole.COUNSELOR:
            managed_ids = current_user.get_managed_class_ids()
            if class_id not in managed_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您没有权限访问该班级的学生"
                )
        query = query.filter(Student.class_id == class_id)

    if name:
        query = query.filter(Student.name.like(f"%{name}%"))

    if student_no:
        query = query.filter(Student.student_no.like(f"%{student_no}%"))

    if grade:
        query = query.filter(Class.grade == str(grade))

    if is_active is not None:
        query = query.filter(Student.is_active == is_active)

    # 统计和分页
    total = query.count()
    students = query.order_by(Student.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 构建响应
    items = []
    for s in students:
        items.append({
            "id": s.id,
            "student_no": s.student_no,
            "name": s.name,
            "gender": s.gender,
            "class_id": s.class_id,
            "class_name": s.class_info.name if s.class_info else None,
            "grade": s.class_info.grade if s.class_info else None,
            "phone": s.phone,
            "email": s.email,
            "is_active": s.is_active,
            "created_at": s.created_at
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{student_id:int}", response_model=dict, summary="获取学生详情")
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if student_id < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="学生ID必须大于0"
        )
    """
    获取学生详情

    权限控制：
    - admin: 可以查看所有学生
    - counselor: 只能查看其管理班级的学生
    - student: 只能查看自己的信息
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    # ========== 权限检查 ==========
    # 检查是否有权限访问该学生
    if not check_student_access(current_user, student_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限访问该学生的信息"
        )

    return {
        "id": student.id,
        "student_no": student.student_no,
        "name": student.name,
        "gender": student.gender,
        "class_id": student.class_id,
        "class_name": student.class_info.name if student.class_info else None,
        "grade": student.class_info.grade if student.class_info else None,
        "phone": student.phone,
        "email": student.email,
        "id_card": getattr(student, 'id_card', None),
        "address": getattr(student, 'address', None),
        "is_active": student.is_active,
        "created_at": student.created_at,
        "updated_at": student.updated_at
    }


@router.post("", response_model=StudentResponse, summary="创建学生")
def create_student(
    data: StudentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_counselor_or_admin)
):
    """
    创建学生（管理员和辅导员可操作）
    """
    # 检查学号是否已存在
    if db.query(Student).filter(Student.student_no == data.student_no).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号已存在"
        )

    # 检查班级是否存在
    class_info = db.query(Class).filter(Class.id == data.class_id).first()
    if not class_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="班级不存在"
        )

    student = Student(**data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)

    return StudentResponse.model_validate(student)


@router.put("/{student_id:int}", response_model=StudentResponse, summary="更新学生")
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin)
):
    """
    更新学生信息（管理员和辅导员可操作）

    辅导员只能更新其管理班级的学生
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    # ========== 权限检查 ==========
    # 辅导员只能修改其管理班级的学生
    if current_user.role == UserRole.COUNSELOR:
        if not check_student_access(current_user, student_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限修改该学生的信息"
            )

        # 如果要更改班级，检查是否有权限访问新班级
        if data.class_id:
            managed_ids = current_user.get_managed_class_ids()
            if data.class_id not in managed_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您没有权限将学生转移到该班级"
                )

    # 更新字段
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(student, key, value)

    db.commit()
    db.refresh(student)

    return StudentResponse.model_validate(student)


@router.delete("/{student_id:int}", summary="删除学生")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin)
):
    """
    删除学生（管理员和辅导员可操作）

    辅导员只能删除其管理班级的学生
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    # ========== 权限检查 ==========
    if current_user.role == UserRole.COUNSELOR:
        if not check_student_access(current_user, student_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限删除该学生"
            )

    db.delete(student)
    db.commit()

    return {"message": "删除成功"}


@router.get("/{student_id:int}/scores", summary="获取学生成绩")
def get_student_scores(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取学生成绩列表

    权限控制：
    - admin: 可以查看所有学生成绩
    - counselor: 只能查看其管理班级学生的成绩
    - student: 只能查看自己的成绩
    """
    # ========== 权限检查 ==========
    if not check_student_access(current_user, student_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限查看该学生的成绩"
        )

    from app.models.score import Score
    from app.models.course import Course

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    scores = db.query(Score).join(Course).filter(
        Score.student_id == student_id
    ).all()

    return {
        "student": {
            "id": student.id,
            "student_no": student.student_no,
            "name": student.name,
            "class_name": student.class_info.name if student.class_info else None
        },
        "scores": [
            {
                "id": s.id,
                "course_id": s.course_id,
                "course_name": s.course.course_name if s.course else None,
                "score": float(s.score) if s.score else None,
                "semester": s.semester,
                "exam_type": s.exam_type,
                "is_passed": s.is_passed
            }
            for s in scores
        ]
    }


@router.get("/{student_id:int}/attendances", summary="获取学生考勤")
def get_student_attendances(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取学生考勤记录

    权限控制：
    - admin: 可以查看所有学生考勤
    - counselor: 只能查看其管理班级学生的考勤
    - student: 只能查看自己的考勤
    """
    # ========== 权限检查 ==========
    if not check_student_access(current_user, student_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限查看该学生的考勤记录"
        )

    from app.models.attendance import Attendance, AttendanceStatus

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    attendances = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).order_by(Attendance.date.desc()).limit(50).all()

    return {
        "student": {
            "id": student.id,
            "student_no": student.student_no,
            "name": student.name,
            "class_name": student.class_info.name if student.class_info else None
        },
        "attendances": [
            {
                "id": a.id,
                "date": a.date.isoformat() if a.date else None,
                "status": a.status.value if a.status else None,
                "course_name": a.course.course_name if a.course else None,
                "remark": a.remark
            }
            for a in attendances
        ]
    }



