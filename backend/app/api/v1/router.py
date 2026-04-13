"""
API V1 路由聚合
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.api.v1 import auth, users_secure as users, students, rules_secure as rules, alerts_secure as alerts, dashboard_secure as dashboard, password, import_export, scores_secure as scores, attendances_secure as attendances, students_classes, courses
from app.api.v1 import classes as classes_module
from app.database import get_db
from app.api.deps import get_current_user, get_accessible_class_ids
from app.models.student import Class
from app.models.user import User

api_router = APIRouter()

# 注册各模块路由
# 注意：students_classes.router 必须在 students.router 之前注册，以避免 /{student_id} 捕获 /classes
api_router.include_router(classes_module.router, prefix="/classes", tags=["班级管理"])
# 注意：students_classes.router 必须在 students.router 之前注册，以避免 /{student_id} 捕获 /classes
api_router.include_router(students_classes.router, prefix="/students", tags=["班级管理"])
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(students.router, prefix="/students", tags=["学生管理"])
api_router.include_router(rules.router, prefix="/rules", tags=["规则管理"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["预警管理"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_router.include_router(password.router, prefix="/password", tags=["密码找回"])
api_router.include_router(import_export.router, prefix="/import", tags=["数据导入导出"])
api_router.include_router(scores.router, prefix="/scores", tags=["成绩管理"])
api_router.include_router(attendances.router, prefix="/attendances", tags=["考勤管理"])
api_router.include_router(courses.router, prefix="/courses", tags=["课程管理"])
