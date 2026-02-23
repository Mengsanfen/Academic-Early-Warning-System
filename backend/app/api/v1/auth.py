"""
认证 API
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.config import settings
from app.models.user import User, UserRole
from app.api.deps import get_current_user as get_current_user_dependency


router = APIRouter()


# ========== Schemas ==========

class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class StudentInfo(BaseModel):
    """学生信息（用于用户响应）"""
    id: int
    name: str
    student_no: str
    class_name: str | None = None
    phone: str | None = None
    avatar: str | None = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    role: UserRole
    name: str | None = None
    nickname: str | None = None
    first_login: bool = False
    email: str | None = None
    student_id: int | None = None
    student: StudentInfo | None = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    require_password_change: bool = False


class RefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


# ========== API 端点 ==========

@router.post("/login", response_model=LoginResponse, summary="用户登录")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录

    - **username**: 用户名
    - **password**: 密码
    """
    # 查找用户
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 验证密码
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    # 生成令牌
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    # 获取用户名称和学生信息
    user_name = None
    student_info = None
    student_id = None

    if user.student:
        user_name = user.student.name
        student_id = user.student.id
        student_info = StudentInfo(
            id=user.student.id,
            name=user.student.name,
            student_no=user.student.student_no,
            class_name=user.student.class_info.name if user.student.class_info else None,
            phone=user.student.phone,
            avatar=user.avatar_url
        )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            name=user_name,
            nickname=user.nickname,
            first_login=user.first_login,
            email=user.email,
            student_id=student_id,
            student=student_info
        ),
        require_password_change=user.first_login
    )


@router.post("/login/form", response_model=LoginResponse, summary="OAuth2表单登录")
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 密码模式登录（用于 Swagger UI）
    """
    return login(LoginRequest(
        username=form_data.username,
        password=form_data.password
    ), db)


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    使用刷新令牌获取新的访问令牌
    """
    user_id = verify_token(request.refresh_token, token_type="refresh")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )

    access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", summary="用户登出")
def logout():
    """
    用户登出

    注：由于使用JWT无状态认证，服务端不维护会话状态
    客户端需要自行删除本地存储的令牌
    """
    return {"message": "登出成功"}


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str | None = None  # 首次登录可不提供
    new_password: str


@router.post("/change-password", summary="修改密码")
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """
    修改密码

    - 首次登录用户无需提供旧密码
    - 非首次登录用户需提供旧密码验证
    """
    # 非首次登录需要验证旧密码
    if not current_user.first_login:
        if not request.old_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请输入原密码"
            )
        if not verify_password(request.old_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="原密码错误"
            )

    # 更新密码
    current_user.password_hash = get_password_hash(request.new_password)
    current_user.first_login = False
    db.commit()

    return {"message": "密码修改成功"}


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """
    获取当前登录用户的详细信息
    """
    # 刷新用户信息（确保获取最新的关联数据）
    user = db.query(User).filter(User.id == current_user.id).first()

    user_name = None
    student_info = None
    student_id = None

    if user.student:
        user_name = user.student.name
        student_id = user.student.id
        student_info = StudentInfo(
            id=user.student.id,
            name=user.student.name,
            student_no=user.student.student_no,
            class_name=user.student.class_info.name if user.student.class_info else None,
            phone=user.student.phone,
            avatar=user.avatar_url
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        name=user_name,
        nickname=user.nickname,
        first_login=user.first_login,
        email=user.email,
        student_id=student_id,
        student=student_info
    )
