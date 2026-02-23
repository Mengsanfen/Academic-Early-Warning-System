"""
密码找回 API
"""
import random
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.core.email import send_verification_email


router = APIRouter()


# ========== 内存存储验证码（生产环境应使用Redis） ==========
verification_codes = {}


# ========== Schemas ==========

class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    email: EmailStr


class SendCodeResponse(BaseModel):
    """发送验证码响应"""
    message: str


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    email: EmailStr
    code: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求（已登录用户）"""
    old_password: str
    new_password: str


# ========== API 端点 ==========

@router.post("/send-code", response_model=SendCodeResponse, summary="发送验证码")
def send_verification_code(
    data: SendCodeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """发送密码找回验证码到邮箱"""
    # 查找用户
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # 为了安全，不暴露用户是否存在
        return {"message": "如果该邮箱已注册，验证码将发送到您的邮箱"}

    # 生成6位验证码
    code = ''.join(random.choices(string.digits, k=6))

    # 存储验证码（5分钟有效期）
    verification_codes[data.email] = {
        "code": code,
        "expires_at": datetime.now() + timedelta(minutes=5),
        "user_id": user.id
    }

    # 异步发送邮件
    background_tasks.add_task(send_verification_email, data.email, code, 5)

    return {"message": "如果该邮箱已注册，验证码将发送到您的邮箱"}


@router.post("/reset", summary="重置密码")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """通过验证码重置密码"""
    # 检查验证码
    stored = verification_codes.get(data.email)

    if not stored:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码无效或已过期"
        )

    if datetime.now() > stored["expires_at"]:
        del verification_codes[data.email]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期"
        )

    if stored["code"] != data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误"
        )

    # 获取用户
    user = db.query(User).filter(User.id == stored["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 更新密码
    user.password_hash = get_password_hash(data.new_password)
    user.first_login = False  # 已通过验证码验证，不算首次登录
    db.commit()

    # 删除已使用的验证码
    del verification_codes[data.email]

    return {"message": "密码重置成功"}


@router.post("/change", summary="修改密码")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(lambda: None)  # TODO: 需要从token获取当前用户
):
    """已登录用户修改密码"""
    from app.api.deps import get_current_user

    # 验证旧密码
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )

    # 更新密码
    current_user.password_hash = get_password_hash(data.new_password)
    current_user.first_login = False
    db.commit()

    return {"message": "密码修改成功"}


@router.post("/first-login-change", summary="首次登录修改密码")
def first_login_change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db)
):
    """首次登录强制修改密码"""
    from app.api.deps import get_current_user

    # 此接口不需要验证旧密码，因为是首次登录
    # 更新密码
    # current_user.password_hash = get_password_hash(data.new_password)
    # current_user.first_login = False
    # db.commit()

    return {"message": "密码修改成功"}
