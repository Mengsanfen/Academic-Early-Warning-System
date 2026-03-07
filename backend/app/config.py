"""
应用配置模块
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "学业预警系统"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # API 配置
    API_V1_PREFIX: str = "/api/v1"

    # 数据库配置 - MySQL
    DATABASE_URL: str = "mysql+pymysql://root:yx1208@localhost:3306/alert_system"

    # Redis 配置 (可选)
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT 配置
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 密码哈希配置
    PASSWORD_HASH_ALGORITHM: str = "bcrypt"

    # CORS 配置
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000"
    ]

    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # 文件上传配置
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

    # 邮件配置 (SMTP)
    SMTP_HOST: str = "smtp.qq.com"  # QQ邮箱SMTP服务器
    SMTP_PORT: int = 465            # SSL端口
    SMTP_USER: str = ""             # 发件邮箱地址
    SMTP_PASSWORD: str = ""         # SMTP授权码（不是邮箱密码）
    SMTP_FROM_EMAIL: str = ""       # 发件人邮箱（同SMTP_USER）
    SMTP_FROM_NAME: str = "学业预警系统"  # 发件人名称
    EMAIL_ENABLED: bool = False     # 是否启用真实邮件发送

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
