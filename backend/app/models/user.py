"""
用户模型
"""
from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, Text, ForeignKey
from sqlalchemy.orm import relationship
from enum import Enum

from app.database import Base
from app.models.base import BaseModel, TimestampMixin


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"          # 管理员
    COUNSELOR = "counselor"  # 辅导员
    STUDENT = "student"      # 学生


class User(Base, BaseModel, TimestampMixin):
    """用户表"""
    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.STUDENT, comment="角色")
    is_active = Column(Boolean, default=True, comment="是否激活")

    # 个人信息字段
    nickname = Column(String(50), nullable=True, comment="昵称")
    email = Column(String(100), nullable=True, comment="邮箱")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    phone = Column(String(20), nullable=True, comment="电话")
    bio = Column(Text, nullable=True, comment="个人简介")
    first_login = Column(Boolean, default=True, comment="是否首次登录")

    # 学生ID外键（仅学生角色用户有值）
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True, comment="关联学生ID")

    # 辅导员管理的班级ID列表（逗号分隔，如 "1,2,3"）
    # 仅对 role='counselor' 有效
    managed_class_ids = Column(Text, nullable=True, comment="管理的班级ID列表(逗号分隔)")

    # 关联关系
    student = relationship("Student", back_populates="user", uselist=False, foreign_keys=[student_id])
    alert_records = relationship("AlertRecord", back_populates="handler")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

    def get_managed_class_ids(self) -> list[int]:
        """
        获取辅导员管理的班级ID列表

        Returns:
            班级ID整数列表，如果不是辅导员或未配置则返回空列表
        """
        if self.role != UserRole.COUNSELOR:
            return []

        if not self.managed_class_ids:
            return []

        try:
            # 解析逗号分隔的ID字符串
            ids = []
            for id_str in self.managed_class_ids.split(','):
                id_str = id_str.strip()
                if id_str:
                    ids.append(int(id_str))
            return ids
        except (ValueError, AttributeError):
            return []

    def has_access_to_class(self, class_id: int) -> bool:
        """
        检查用户是否有权限访问指定班级

        Args:
            class_id: 班级ID

        Returns:
            True 如果有权限访问
        """
        # 管理员有权访问所有班级
        if self.role == UserRole.ADMIN:
            return True

        # 辅导员只能访问其管理的班级
        if self.role == UserRole.COUNSELOR:
            managed_ids = self.get_managed_class_ids()
            return class_id in managed_ids

        # 学生没有班级访问权限
        return False

    def has_access_to_student(self, student) -> bool:
        """
        检查用户是否有权限访问指定学生

        Args:
            student: 学生对象

        Returns:
            True 如果有权限访问
        """
        if not student:
            return False

        # 管理员有权访问所有学生
        if self.role == UserRole.ADMIN:
            return True

        # 辅导员只能访问其管理班级的学生
        if self.role == UserRole.COUNSELOR:
            if not student.class_id:
                return False
            return self.has_access_to_class(student.class_id)

        # 学生只能访问自己
        if self.role == UserRole.STUDENT:
            return self.student and self.student.id == student.id

        return False
