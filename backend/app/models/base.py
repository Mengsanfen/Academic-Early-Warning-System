"""
基础模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.orm import declared_attr


class TimestampMixin:
    """时间戳混入类"""

    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=datetime.now, nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime,
            default=datetime.now,
            onupdate=datetime.now,
            nullable=False
        )


class BaseModel:
    """基础模型类"""

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
