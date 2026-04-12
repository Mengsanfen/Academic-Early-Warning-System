"""
规则模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import BaseModel, TimestampMixin

COMPREHENSIVE_RULE_CODE = "COMPREHENSIVE_RISK"
COMPREHENSIVE_RULE_MODE = "comprehensive"


class RuleType(str, enum.Enum):
    """规则类型枚举"""
    SCORE = "score"          # 成绩预警
    ATTENDANCE = "attendance"  # 出勤预警
    GRADUATION = "graduation"  # 毕业风险预警


class AlertLevel(str, enum.Enum):
    """预警级别枚举"""
    WARNING = "warning"    # 一般警告
    SERIOUS = "serious"    # 严重
    URGENT = "urgent"      # 紧急


class Rule(Base, BaseModel, TimestampMixin):
    """规则表"""
    __tablename__ = "rules"

    name = Column(String(100), nullable=False, comment="规则名称")
    code = Column(String(50), unique=True, nullable=False, index=True, comment="规则编码")
    type = Column(SQLEnum(RuleType), nullable=False, comment="规则类型")
    conditions = Column(JSON, nullable=False, comment="规则条件(JSON格式)")
    level = Column(SQLEnum(AlertLevel), nullable=False, comment="预警级别")
    description = Column(Text, nullable=True, comment="规则描述")
    message_template = Column(String(255), nullable=True, comment="预警消息模板")
    is_active = Column(Boolean, default=True, comment="是否启用")

    # 关联关系
    alerts = relationship("Alert", back_populates="rule")

    def __repr__(self):
        return f"<Rule(id={self.id}, code={self.code}, name={self.name})>"
