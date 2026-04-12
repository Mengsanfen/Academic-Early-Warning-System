"""
数据库连接模块
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from app.config import settings
from app.schema_sync import ensure_runtime_schema

# MySQL 配置
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 自动检测断开的连接
    pool_recycle=3600,   # 每小时回收连接，避免 MySQL 8小时超时
    echo=settings.DEBUG,
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """
    获取数据库会话（依赖注入）

    Yields:
        Session: 数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    from app.models import (  # noqa: F401
        user, student, course, score, attendance, rule, alert
    )
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)
