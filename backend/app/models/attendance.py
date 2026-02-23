"""
考勤模型
"""
from sqlalchemy import Column, Integer, String, Date, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import BaseModel, TimestampMixin


class AttendanceStatus(str, enum.Enum):
    """考勤状态枚举"""
    PRESENT = "present"    # 出勤
    ABSENT = "absent"      # 缺勤
    LATE = "late"          # 迟到
    LEAVE = "leave"        # 请假


class Attendance(Base, BaseModel, TimestampMixin):
    """考勤表"""
    __tablename__ = "attendances"

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True, comment="学生ID")
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True, comment="课程ID")
    date = Column(Date, nullable=False, index=True, comment="考勤日期")
    status = Column(SQLEnum(AttendanceStatus), nullable=False, comment="考勤状态")
    remark = Column(String(255), nullable=True, comment="备注")

    # 关联关系
    student = relationship("Student", back_populates="attendances")
    course = relationship("Course", back_populates="attendances")

    def __repr__(self):
        return f"<Attendance(id={self.id}, student_id={self.student_id}, date={self.date}, status={self.status})>"
