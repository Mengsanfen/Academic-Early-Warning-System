"""
课程模型
"""
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import BaseModel, TimestampMixin


def _enum_values(enum_cls):
    return [item.value for item in enum_cls]


class CourseType(str, enum.Enum):
    """课程类型枚举"""
    REQUIRED = "required"      # 必修课
    ELECTIVE = "elective"      # 选修课
    PUBLIC = "public"          # 公共课
    PROFESSIONAL = "professional"  # 专业课
    PRACTICE = "practice"      # 实践课


class Course(Base, BaseModel, TimestampMixin):
    """课程表"""
    __tablename__ = "courses"

    course_code = Column(String(20), unique=True, nullable=False, index=True, comment="课程代码")
    course_name = Column(String(100), nullable=False, comment="课程名称")
    credit = Column(Numeric(3, 1), nullable=False, comment="学分")
    semester = Column(String(20), nullable=False, index=True, comment="学期(如:2025-2026-1)")
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True, comment="授课班级ID")
    teacher_name = Column(String(50), nullable=True, comment="授课教师")
    course_type = Column(
        SQLEnum(CourseType, values_callable=_enum_values, native_enum=False),
        nullable=False,
        default=CourseType.REQUIRED,
        comment="课程类型: required-必修, elective-选修, public-公共, professional-专业, practice-实践"
    )

    # 关联关系
    class_info = relationship("Class", back_populates="courses")
    scores = relationship("Score", back_populates="course")
    attendances = relationship("Attendance", back_populates="course")

    def __repr__(self):
        return f"<Course(id={self.id}, course_name={self.course_name})>"
