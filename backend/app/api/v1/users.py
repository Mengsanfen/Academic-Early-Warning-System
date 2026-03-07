"""
用户管理 API

包含用户管理和权限配置功能
"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.api.deps import get_admin_user, get_current_user
from app.models.user import User, UserRole
from app.config import settings


router = APIRouter()


# ========== Schemas ==========

class UserCreate(BaseModel):
    """创建用户"""
    username: str
    password: str
    role: UserRole
    student_id: Optional[int] = None
    managed_class_ids: Optional[str] = None  # 辅导员管理的班级ID列表


class UserUpdate(BaseModel):
    """更新用户（管理员）"""
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    """更新个人信息"""
    nickname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    role: UserRole
    student_id: Optional[int]
    managed_class_ids: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class CounselorUpdate(BaseModel):
    """更新辅导员信息"""
    managed_class_ids: str  # 逗号分隔的班级ID列表


class UserProfileResponse(BaseModel):
    """用户个人信息响应"""
    id: int
    username: str
    role: UserRole
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    first_login: bool
    created_at: Optional[datetime] = None
    # 关联的学生信息（如果是学生用户）
    student_name: Optional[str] = None
    student_no: Optional[str] = None
    class_name: Optional[str] = None
    # 辅导员管理的班级名称列表
    managed_class_names: Optional[List[str]] = None

    class Config:
        from_attributes = True


# ========== API 端点 ==========

@router.get("", response_model=dict, summary="获取用户列表")
def get_users(
    page: int = 1,
    page_size: int = 20,
    role: Optional[UserRole] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user)
):
    """获取用户列表（管理员）

    支持通过 search 参数搜索用户名、学号、学生姓名
    """
    from sqlalchemy.orm import joinedload, contains_eager
    from app.models.student import Student

    query = db.query(User).outerjoin(Student, User.student_id == Student.id)
    query = query.options(contains_eager(User.student).joinedload(Student.class_info))

    if role:
        query = query.filter(User.role == role)

    # 搜索功能：用户名、学号、学生姓名
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_pattern)) |
            (User.nickname.ilike(search_pattern)) |
            (Student.student_no.ilike(search_pattern)) |
            (Student.name.ilike(search_pattern))
        )

    # 去重（因为 join 可能产生重复行）
    query = query.distinct()

    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [UserResponse.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("", response_model=UserResponse, summary="创建用户")
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user)
):
    """创建用户（管理员）"""
    # 检查用户名是否存在
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    from app.core.security import get_password_hash

    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        role=data.role,
        student_id=data.student_id,
        managed_class_ids=data.managed_class_ids if data.role == UserRole.COUNSELOR else None
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/counselors", response_model=dict, summary="获取辅导员列表")
def get_counselors(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user)
):
    """获取所有辅导员列表（管理员）

    用于管理员查看和配置辅导员的管理班级
    """
    from app.models.student import Class

    counselors = db.query(User).filter(User.role == UserRole.COUNSELOR).all()

    # 获取所有班级
    all_classes = db.query(Class).all()
    class_map = {c.id: c.name for c in all_classes}

    items = []
    for c in counselors:
        managed_ids = c.get_managed_class_ids()
        managed_names = [class_map.get(cid, f"班级{cid}") for cid in managed_ids]

        items.append({
            "id": c.id,
            "username": c.username,
            "managed_class_ids": c.managed_class_ids,
            "managed_class_names": managed_names,
            "is_active": c.is_active,
            "created_at": c.created_at
        })

    return {
        "items": items,
        "total": len(items)
    }


@router.put("/counselors/{user_id}/classes", summary="设置辅导员管理班级")
def set_counselor_classes(
    user_id: int,
    data: CounselorUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user)
):
    """
    设置辅导员管理的班级（管理员）

    Args:
        user_id: 用户ID
        data.managed_class_ids: 逗号分隔的班级ID列表，如 "1,2,3"
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if user.role != UserRole.COUNSELOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能为辅导员设置管理班级"
        )

    # 验证班级ID是否存在
    from app.models.student import Class

    if data.managed_class_ids:
        try:
            class_ids = [int(id_str.strip()) for id_str in data.managed_class_ids.split(',') if id_str.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="班级ID格式错误，应为逗号分隔的数字"
            )

        # 验证所有班级是否存在
        existing_classes = db.query(Class.id).filter(Class.id.in_(class_ids)).all()
        existing_ids = [c[0] for c in existing_classes]

        invalid_ids = set(class_ids) - set(existing_ids)
        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"以下班级ID不存在: {', '.join(map(str, invalid_ids))}"
            )

    user.managed_class_ids = data.managed_class_ids
    db.commit()
    db.refresh(user)

    return {
        "message": "辅导员管理班级设置成功",
        "user_id": user.id,
        "managed_class_ids": user.managed_class_ids,
        "managed_class_ids_list": user.get_managed_class_ids()
    }


@router.get("/me", response_model=UserProfileResponse, summary="获取当前用户信息")
def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前登录用户的完整个人信息"""
    from app.models.student import Class

    response_data = {
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
        "student_name": None,
        "student_no": None,
        "class_name": None,
        "managed_class_names": None
    }

    # 如果是学生用户，获取关联的学生信息
    if current_user.student:
        response_data["student_name"] = current_user.student.name
        response_data["student_no"] = current_user.student.student_no
        response_data["class_name"] = current_user.student.class_info.name if current_user.student.class_info else None

    # 如果是辅导员，获取管理的班级名称
    if current_user.role == UserRole.COUNSELOR:
        managed_ids = current_user.get_managed_class_ids()
        if managed_ids:
            classes = db.query(Class).filter(Class.id.in_(managed_ids)).all()
            response_data["managed_class_names"] = [c.name for c in classes]

    return UserProfileResponse(**response_data)


@router.put("/me", response_model=UserProfileResponse, summary="更新个人信息")
def update_current_user_profile(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新当前用户的个人信息"""
    from app.models.student import Class

    # 更新字段
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

    # 返回更新后的信息
    response_data = {
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
        "student_name": None,
        "student_no": None,
        "class_name": None,
        "managed_class_names": None
    }

    if current_user.student:
        response_data["student_name"] = current_user.student.name
        response_data["student_no"] = current_user.student.student_no
        response_data["class_name"] = current_user.student.class_info.name if current_user.student.class_info else None

    # 如果是辅导员，获取管理的班级名称
    if current_user.role == UserRole.COUNSELOR:
        managed_ids = current_user.get_managed_class_ids()
        if managed_ids:
            classes = db.query(Class).filter(Class.id.in_(managed_ids)).all()
            response_data["managed_class_names"] = [c.name for c in classes]

    return UserProfileResponse(**response_data)


@router.post("/me/avatar", summary="上传头像")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上传用户头像"""
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持 JPG、PNG、GIF、WebP 格式的图片"
        )

    # 验证文件大小 (最大 2MB)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片大小不能超过 2MB"
        )

    # 创建上传目录
    upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    # 生成文件名
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(upload_dir, filename)

    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)

    # 更新用户头像URL
    avatar_url = f"/uploads/avatars/{filename}"
    current_user.avatar_url = avatar_url
    db.commit()

    return {
        "message": "头像上传成功",
        "avatar_url": avatar_url
    }


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user)
):
    """获取用户详情（管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户")
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user)
):
    """更新用户（管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 禁止禁用管理员账号
    if user.role == UserRole.ADMIN and data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用管理员账号"
        )

    if data.password:
        from app.core.security import get_password_hash
        user.password_hash = get_password_hash(data.password)

    if data.is_active is not None:
        user.is_active = data.is_active

    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.delete("/{user_id}", summary="删除用户")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user)
):
    """删除用户（管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 禁止删除管理员账号
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除管理员账号"
        )

    db.delete(user)
    db.commit()

    return {"message": "删除成功"}
