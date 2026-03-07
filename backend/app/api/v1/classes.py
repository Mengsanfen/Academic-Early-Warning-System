"""
班级管理 API
"""
from fastapi import APIRouter, Depends
from typing import Optional

from app.api.deps import get_current_user, get_accessible_class_ids
from app.database import get_db
from app.models.user import User
from sqlalchemy.orm import Session, joinedload
from app.models.student import Class

router = APIRouter()


@router.get("")
def get_classes(
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
