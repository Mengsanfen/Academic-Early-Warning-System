"""
学生和班级模型
"""
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import BaseModel, TimestampMixin


class Gender(str, enum.Enum):
    """性别枚举"""
    MALE = "male"
    FEMALE = "female"


class StudentStatus(str, enum.Enum):
    """学生状态枚举"""
    ACTIVE = "active"        # 在读
    SUSPENDED = "suspended"  # 休学
    GRADUATED = "graduated"  # 已毕业


class Department(Base, BaseModel, TimestampMixin):
    """院系表"""
    __tablename__ = "departments"

    name = Column(String(100), nullable=False, comment="院系名称")
    code = Column(String(20), unique=True, nullable=True, comment="院系代码")

    # 关联关系
    classes = relationship("Class", back_populates="department")

    def __repr__(self):
        return f"<Department(id={self.id}, name={self.name})>"


class Class(Base, BaseModel, TimestampMixin):
    """班级表"""
    __tablename__ = "classes"

    name = Column(String(100), nullable=False, comment="班级名称")
    grade = Column(String(20), nullable=False, comment="年级")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, comment="院系ID")
    counselor_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="辅导员ID")

    # 关联关系
    department = relationship("Department", back_populates="classes")
    students = relationship("Student", back_populates="class_info")
    courses = relationship("Course", back_populates="class_info")

    def __repr__(self):
        return f"<Class(id={self.id}, name={self.name})>"


class Student(Base, BaseModel, TimestampMixin):
    """学生表"""
    __tablename__ = "students"

    student_no = Column(String(20), unique=True, nullable=False, index=True, comment="学号")
    name = Column(String(50), nullable=False, comment="姓名")
    gender = Column(String(10), nullable=True, comment="性别")
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, comment="班级ID")
    enroll_year = Column(Integer, nullable=True, comment="入学年份")
    phone = Column(String(20), nullable=True, comment="联系电话")
    email = Column(String(100), nullable=True, comment="邮箱")
    status = Column(
        SQLEnum(StudentStatus),
        nullable=False,
        default=StudentStatus.ACTIVE,
        comment="状态"
    )
    profile = Column(String(20), nullable=True, default="normal", comment="学生画像")
    is_active = Column(Boolean, default=True, comment="是否在读")

    # 关联关系
    class_info = relationship("Class", back_populates="students")
    user = relationship("User", back_populates="student", foreign_keys="[User.student_id]")
    scores = relationship("Score", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")
    alerts = relationship("Alert", back_populates="student")

    def __repr__(self):
        return f"<Student(id={self.id}, student_no={self.student_no}, name={self.name})>"

    @property
    def class_name(self) -> str:
        """获取班级名称"""
        return self.class_info.name if self.class_info else ""
