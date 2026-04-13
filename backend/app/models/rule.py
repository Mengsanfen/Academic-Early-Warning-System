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


def _enum_values(enum_cls):
    return [item.value for item in enum_cls]


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


class TargetType(str, enum.Enum):
    """规则目标类型枚举"""
    ALL = "all"            # 全部学生
    GRADES = "grades"      # 按年级
    CLASSES = "classes"    # 按班级


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

    # 规则目标范围配置
    target_type = Column(
        SQLEnum(TargetType, values_callable=_enum_values, native_enum=False),
        nullable=False,
        default=TargetType.ALL,
        comment="目标类型: all-全部, grades-按年级, classes-按班级"
    )
    target_grades = Column(JSON, nullable=True, comment="目标年级列表，如['2022级', '2023级']")
    target_classes = Column(JSON, nullable=True, comment="目标班级ID列表，如[1, 2, 3]")

    # 关联关系
    alerts = relationship("Alert", back_populates="rule")

    def __repr__(self):
        return f"<Rule(id={self.id}, code={self.code}, name={self.name})>"

    def get_target_students_query(self, db):
        """
        获取该规则目标范围内的学生查询对象

        Args:
            db: 数据库会话

        Returns:
            学生查询对象
        """
        from app.models.student import Student, Class

        query = db.query(Student).filter(Student.is_active == True)

        if self.target_type == TargetType.ALL:
            # 全部学生，不额外过滤
            return query

        elif self.target_type == TargetType.GRADES:
            # 按年级筛选
            if self.target_grades and isinstance(self.target_grades, list):
                query = query.join(Class).filter(Class.grade.in_(self.target_grades))
            return query

        elif self.target_type == TargetType.CLASSES:
            # 按班级筛选
            if self.target_classes and isinstance(self.target_classes, list):
                query = query.filter(Student.class_id.in_(self.target_classes))
            return query

        return query
