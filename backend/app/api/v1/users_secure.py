"""
User management APIs with counselor class assignment support.
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_admin_user, get_current_user
from app.config import settings
from app.core.security import get_password_hash
from app.database import get_db
from app.models.student import Class, Student
from app.models.user import User, UserRole


router = APIRouter()


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    student_id: Optional[int] = None
    managed_class_ids: list[int] = Field(default_factory=list)


class UserUpdate(BaseModel):
    password: Optional[str] = None
    is_active: Optional[bool] = None
    managed_class_ids: Optional[list[int]] = None


class CounselorClassUpdate(BaseModel):
    managed_class_ids: list[int] = Field(default_factory=list)


class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None


def _serialize_class(class_item: Class) -> dict:
    return {
        "id": class_item.id,
        "name": class_item.name,
        "grade": class_item.grade,
        "department_id": class_item.department_id,
    }


def _normalize_class_ids(class_ids: Optional[list[int]]) -> list[int]:
    if not class_ids:
        return []
    normalized = sorted({int(class_id) for class_id in class_ids})
    if any(class_id <= 0 for class_id in normalized):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="班级ID必须为正整数")
    return normalized


def _validate_classes(db: Session, class_ids: list[int]) -> list[Class]:
    if not class_ids:
        return []
    classes = db.query(Class).filter(Class.id.in_(class_ids)).order_by(Class.id.asc()).all()
    existing_ids = {class_item.id for class_item in classes}
    missing_ids = [class_id for class_id in class_ids if class_id not in existing_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"以下班级不存在: {', '.join(map(str, missing_ids))}",
        )
    return classes


def _class_ids_to_text(class_ids: list[int]) -> Optional[str]:
    return ",".join(str(class_id) for class_id in class_ids) if class_ids else None


def _serialize_user(user: User, class_lookup: Optional[dict[int, Class]] = None) -> dict:
    managed_ids = user.get_managed_class_ids()
    classes = [class_lookup[class_id] for class_id in managed_ids if class_lookup and class_id in class_lookup]
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role.value if hasattr(user.role, "value") else user.role,
        "student_id": user.student_id,
        "is_active": user.is_active,
        "managed_class_ids": user.managed_class_ids,
        "managed_class_ids_list": managed_ids,
        "managed_class_names": [item.name for item in classes],
        "managed_classes": [_serialize_class(item) for item in classes],
        "student": {
            "id": user.student.id,
            "student_no": user.student.student_no,
            "name": user.student.name,
            "class_name": user.student.class_info.name if user.student.class_info else None,
        } if user.student else None,
        "created_at": user.created_at,
    }


def _assign_counselor_classes(db: Session, user: User, class_ids: list[int]) -> list[Class]:
    classes = _validate_classes(db, class_ids)
    user.managed_class_ids = _class_ids_to_text(class_ids)
    return classes


@router.get("", response_model=dict, summary="获取用户列表")
def get_users(
    page: int = 1,
    page_size: int = 20,
    role: Optional[UserRole] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    query = db.query(User).options(joinedload(User.student).joinedload(Student.class_info))

    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        search_pattern = f"%{search}%"
        query = query.outerjoin(Student, User.student_id == Student.id).filter(
            (User.username.ilike(search_pattern))
            | (User.nickname.ilike(search_pattern))
            | (Student.student_no.ilike(search_pattern))
            | (Student.name.ilike(search_pattern))
        )

    total = query.distinct().count()
    users = (
        query.distinct()
        .order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    all_class_ids = {class_id for user in users for class_id in user.get_managed_class_ids()}
    class_lookup = {
        class_item.id: class_item
        for class_item in db.query(Class).filter(Class.id.in_(all_class_ids)).all()
    } if all_class_ids else {}

    return {
        "items": [_serialize_user(user, class_lookup) for user in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/class-options", response_model=dict, summary="获取班级选项")
def get_class_options(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    classes = db.query(Class).order_by(Class.grade.desc(), Class.name.asc()).all()
    return {"items": [_serialize_class(class_item) for class_item in classes]}


@router.get("/counselors", response_model=dict, summary="获取辅导员列表")
def get_counselors(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    counselors = db.query(User).filter(User.role == UserRole.COUNSELOR).order_by(User.id.desc()).all()
    all_class_ids = {class_id for user in counselors for class_id in user.get_managed_class_ids()}
    class_lookup = {
        class_item.id: class_item
        for class_item in db.query(Class).filter(Class.id.in_(all_class_ids)).all()
    } if all_class_ids else {}
    return {
        "items": [_serialize_user(user, class_lookup) for user in counselors],
        "total": len(counselors),
    }


@router.post("", response_model=dict, summary="创建用户")
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    if data.role == UserRole.STUDENT and not data.student_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="学生账号必须关联学生")

    normalized_class_ids = _normalize_class_ids(data.managed_class_ids)
    if data.role != UserRole.COUNSELOR:
        normalized_class_ids = []

    if data.student_id:
        student = db.query(Student).filter(Student.id == data.student_id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="关联学生不存在")

    _validate_classes(db, normalized_class_ids)

    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        role=data.role,
        student_id=data.student_id,
        managed_class_ids=_class_ids_to_text(normalized_class_ids),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    class_lookup = {
        class_item.id: class_item
        for class_item in db.query(Class).filter(Class.id.in_(normalized_class_ids)).all()
    } if normalized_class_ids else {}
    return _serialize_user(user, class_lookup)


@router.put("/counselors/{user_id}/classes", response_model=dict, summary="设置辅导员管理班级")
def set_counselor_classes(
    user_id: int,
    data: CounselorClassUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.role != UserRole.COUNSELOR:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能为辅导员配置班级权限")

    class_ids = _normalize_class_ids(data.managed_class_ids)
    classes = _assign_counselor_classes(db, user, class_ids)
    db.commit()
    db.refresh(user)

    return {
        "message": "辅导员管理班级设置成功",
        "user": _serialize_user(user, {item.id: item for item in classes}),
    }


@router.get("/me", response_model=dict, summary="获取当前用户信息")
def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    managed_ids = current_user.get_managed_class_ids()
    classes = db.query(Class).filter(Class.id.in_(managed_ids)).all() if managed_ids else []
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "nickname": current_user.nickname,
        "avatar_url": current_user.avatar_url,
        "email": current_user.email,
        "phone": current_user.phone,
        "bio": current_user.bio,
        "is_active": current_user.is_active,
        "first_login": current_user.first_login,
        "created_at": current_user.created_at,
        "student_name": current_user.student.name if current_user.student else None,
        "student_no": current_user.student.student_no if current_user.student else None,
        "class_name": current_user.student.class_info.name if current_user.student and current_user.student.class_info else None,
        "managed_class_names": [item.name for item in classes] if classes else None,
    }


@router.put("/me", response_model=dict, summary="更新个人信息")
def update_current_user_profile(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.nickname is not None:
        current_user.nickname = data.nickname
    if data.email is not None:
        current_user.email = data.email
    if data.phone is not None:
        current_user.phone = data.phone
    if data.bio is not None:
        current_user.bio = data.bio

    db.commit()
    db.refresh(current_user)
    return get_current_user_info(db, current_user)


@router.post("/me/avatar", summary="上传头像")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 JPG、PNG、GIF、WebP 图片")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片大小不能超过 2MB")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as file_obj:
        file_obj.write(content)

    current_user.avatar_url = f"/uploads/avatars/{filename}"
    db.commit()
    return {"message": "头像上传成功", "avatar_url": current_user.avatar_url}


@router.get("/{user_id}", response_model=dict, summary="获取用户详情")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    user = (
        db.query(User)
        .options(joinedload(User.student).joinedload(Student.class_info))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    managed_ids = user.get_managed_class_ids()
    class_lookup = {
        class_item.id: class_item
        for class_item in db.query(Class).filter(Class.id.in_(managed_ids)).all()
    } if managed_ids else {}
    return _serialize_user(user, class_lookup)


@router.put("/{user_id}", response_model=dict, summary="更新用户")
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if user.role == UserRole.ADMIN and data.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能禁用管理员账号")

    if data.password:
        user.password_hash = get_password_hash(data.password)
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.managed_class_ids is not None:
        if user.role != UserRole.COUNSELOR:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有辅导员可配置管理班级")
        class_ids = _normalize_class_ids(data.managed_class_ids)
        _assign_counselor_classes(db, user, class_ids)

    db.commit()
    db.refresh(user)

    managed_ids = user.get_managed_class_ids()
    class_lookup = {
        class_item.id: class_item
        for class_item in db.query(Class).filter(Class.id.in_(managed_ids)).all()
    } if managed_ids else {}
    return _serialize_user(user, class_lookup)


@router.delete("/{user_id}", response_model=dict, summary="删除用户")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除管理员账号")

    db.delete(user)
    db.commit()
    return {"message": "删除成功"}
