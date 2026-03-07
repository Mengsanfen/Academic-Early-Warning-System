"""
预警模型
"""
from sqlalchemy import Column, Integer, String, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import BaseModel, TimestampMixin
from app.models.rule import AlertLevel


class AlertStatus(str, enum.Enum):
    """预警状态枚举"""
    PENDING = "pending"        # 待处理
    PROCESSING = "processing"  # 处理中
    RESOLVED = "resolved"      # 已解决
    IGNORED = "ignored"        # 已忽略


class Alert(Base, BaseModel, TimestampMixin):
    """预警表"""
    __tablename__ = "alerts"

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True, comment="学生ID")
    rule_id = Column(Integer, ForeignKey("rules.id"), nullable=False, comment="触发规则ID")
    level = Column(SQLEnum(AlertLevel), nullable=False, comment="预警级别")
    message = Column(Text, nullable=False, comment="预警信息")
    status = Column(
        SQLEnum(AlertStatus),
        nullable=False,
        default=AlertStatus.PENDING,
        comment="状态"
    )
    semester = Column(String(20), nullable=True, comment="学期")

    # 关联关系
    student = relationship("Student", back_populates="alerts")
    rule = relationship("Rule", back_populates="alerts")
    records = relationship("AlertRecord", back_populates="alert", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Alert(id={self.id}, student_id={self.student_id}, level={self.level}, status={self.status})>"


class AlertRecord(Base, BaseModel, TimestampMixin):
    """预警处理记录表"""
    __tablename__ = "alert_records"

    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False, index=True, comment="预警ID")
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="处理人ID")
    action = Column(String(100), nullable=False, comment="处理动作")
    result = Column(Text, nullable=True, comment="处理结果")

    # 关联关系
    alert = relationship("Alert", back_populates="records")
    handler = relationship("User", back_populates="alert_records")

    def __repr__(self):
        return f"<AlertRecord(id={self.id}, alert_id={self.alert_id}, action={self.action})>"
