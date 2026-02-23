"""
班级列表路由（独立模块，避免与 students.router 的 /{student_id} 冲突）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user, get_accessible_class_ids
from app.models.student import Class
from app.models.user import User

router = APIRouter()


@router.get("/classes", summary="获取班级列表")
def get_students_classes(
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
        return {"items": [], "total": 0}

    query = db.query(Class).options(joinedload(Class.department))

    if class_ids is not None:
        query = query.filter(Class.id.in_(class_ids))

    if department_id:
        query = query.filter(Class.department_id == department_id)

    classes = query.order_by(Class.id.desc()).all()

    items = [
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

    return {
        "items": items,
        "total": len(items)
    }


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
        return {"classes": []}

    query = db.query(Class).options(joinedload(Class.department))

    if class_ids is not None:
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
