"""
成绩模型
"""
from sqlalchemy import Column, Integer, Numeric, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import BaseModel, TimestampMixin


class Score(Base, BaseModel, TimestampMixin):
    """成绩表"""
    __tablename__ = "scores"

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True, comment="学生ID")
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True, comment="课程ID")
    score = Column(Numeric(5, 2), nullable=False, comment="成绩(0-100)")
    semester = Column(String(20), nullable=False, index=True, comment="学期")
    exam_type = Column(String(20), nullable=True, comment="考试类型(期末/补考/重修)")

    # 关联关系
    student = relationship("Student", back_populates="scores")
    course = relationship("Course", back_populates="scores")

    def __repr__(self):
        return f"<Score(id={self.id}, student_id={self.student_id}, score={self.score})>"

    @property
    def is_passed(self) -> bool:
        """是否及格"""
        return float(self.score) >= 60
