"""
API 依赖注入

包含认证、权限控制和数据过滤功能
"""
from typing import Generator, Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, Query
from sqlalchemy import or_

from app.database import get_db
from app.core.security import verify_token
from app.models.user import User, UserRole


# Bearer 认证方案
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前登录用户

    Raises:
        HTTPException: 未认证或用户不存在
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = verify_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户
    """
    return current_user


def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取管理员用户（需要管理员权限）

    Raises:
        HTTPException: 权限不足
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


def get_counselor_or_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取辅导员或管理员用户

    Raises:
        HTTPException: 权限不足
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.COUNSELOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要辅导员或管理员权限"
        )
    return current_user


def get_student_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取学生用户（仅限学生角色）

    Raises:
        HTTPException: 权限不足
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要学生权限"
        )

    if not current_user.student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账号未关联学生信息"
        )

    return current_user


# ==================== 数据权限过滤 ====================

def apply_class_filter(
    query: Query,
    current_user: User,
    class_id_field
) -> Query:
    """
    根据用户角色应用班级数据过滤

    Args:
        query: SQLAlchemy 查询对象
        current_user: 当前登录用户
        class_id_field: 班级ID字段（如 Student.class_id）

    Returns:
        过滤后的查询对象

    注意：
        - admin 用户：不过滤，返回全部数据
        - counselor 用户：只返回其管理班级的数据
        - student 用户：返回空结果（学生无班级权限）
    """
    if current_user.role == UserRole.ADMIN:
        # 管理员可以查看所有数据
        return query

    if current_user.role == UserRole.COUNSELOR:
        # 辅导员只能查看其管理的班级数据
        managed_class_ids = current_user.get_managed_class_ids()

        if not managed_class_ids:
            # 未配置管理班级，返回空结果
            return query.filter(class_id_field == -1)

        # 过滤只显示管理班级的数据
        return query.filter(class_id_field.in_(managed_class_ids))

    # 其他角色无权限
    return query.filter(class_id_field == -1)


def apply_student_filter(
    query: Query,
    current_user: User,
    student_id_field
) -> Query:
    """
    根据用户角色应用学生数据过滤

    Args:
        query: SQLAlchemy 查询对象
        current_user: 当前登录用户
        student_id_field: 学生ID字段

    Returns:
        过滤后的查询对象
    """
    if current_user.role == UserRole.ADMIN:
        return query

    if current_user.role == UserRole.COUNSELOR:
        # 辅导员只能查看其管理班级的学生
        from app.models.student import Student

        managed_class_ids = current_user.get_managed_class_ids()

        if not managed_class_ids:
            return query.filter(student_id_field == -1)

        # 子查询：获取管理班级内的学生ID
        allowed_student_ids = query.session.query(Student.id).filter(
            Student.class_id.in_(managed_class_ids)
        ).subquery()

        return query.filter(student_id_field.in_(allowed_student_ids))

    if current_user.role == UserRole.STUDENT:
        # 学生只能查看自己的数据
        if current_user.student:
            return query.filter(student_id_field == current_user.student.id)
        return query.filter(student_id_field == -1)

    return query.filter(student_id_field == -1)


def check_class_access(
    current_user: User,
    class_id: int
) -> bool:
    """
    检查用户是否有权限访问指定班级

    Args:
        current_user: 当前用户
        class_id: 班级ID

    Returns:
        True 如果有权限
    """
    if current_user.role == UserRole.ADMIN:
        return True

    if current_user.role == UserRole.COUNSELOR:
        managed_ids = current_user.get_managed_class_ids()
        return class_id in managed_ids

    return False


def check_student_access(
    current_user: User,
    student_id: int,
    db: Session
) -> bool:
    """
    检查用户是否有权限访问指定学生

    Args:
        current_user: 当前用户
        student_id: 学生ID
        db: 数据库会话

    Returns:
        True 如果有权限
    """
    from app.models.student import Student

    if current_user.role == UserRole.ADMIN:
        return True

    if current_user.role == UserRole.STUDENT:
        return current_user.student and current_user.student.id == student_id

    if current_user.role == UserRole.COUNSELOR:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student or not student.class_id:
            return False
        return check_class_access(current_user, student.class_id)

    return False


def get_accessible_class_ids(current_user: User) -> Optional[List[int]]:
    """
    获取当前用户可访问的班级ID列表

    Args:
        current_user: 当前用户

    Returns:
        可访问的班级ID列表，None 表示可访问所有班级
    """
    if current_user.role == UserRole.ADMIN:
        return None  # None 表示无限制

    if current_user.role == UserRole.COUNSELOR:
        return current_user.get_managed_class_ids()

    return []  # 空列表表示无权限


