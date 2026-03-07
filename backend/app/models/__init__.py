"""
数据库模型导出
"""
from app.models.base import BaseModel, TimestampMixin
from app.models.user import User, UserRole
from app.models.student import Student, Class, Department, Gender, StudentStatus
from app.models.course import Course
from app.models.score import Score
from app.models.attendance import Attendance, AttendanceStatus
from app.models.rule import Rule, RuleType, AlertLevel
from app.models.alert import Alert, AlertRecord, AlertStatus

__all__ = [
    # 基类
    "BaseModel",
    "TimestampMixin",
    # 用户
    "User",
    "UserRole",
    # 学生相关
    "Student",
    "Class",
    "Department",
    "Gender",
    "StudentStatus",
    # 课程
    "Course",
    # 成绩
    "Score",
    # 考勤
    "Attendance",
    "AttendanceStatus",
    # 规则
    "Rule",
    "RuleType",
    "AlertLevel",
    # 预警
    "Alert",
    "AlertRecord",
    "AlertStatus",
]
