"""
预警管理 API

包含基于用户角色的数据权限过滤
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from app.database import get_db
from app.api.deps import (
    get_current_user,
    get_counselor_or_admin,
    apply_student_filter,
    check_student_access,
    get_accessible_class_ids
)
from app.models.user import User, UserRole
from app.models.alert import Alert, AlertRecord, AlertStatus
from app.models.rule import AlertLevel
from app.models.student import Student


logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Schemas ==========

class AlertResponse(BaseModel):
    """预警响应"""
    id: int
    student_id: int
    student_name: Optional[str] = None
    student_no: Optional[str] = None
    class_name: Optional[str] = None
    rule_id: int
    rule_name: Optional[str] = None
    rule_type: Optional[str] = None
    level: AlertLevel
    message: str
    status: AlertStatus
    created_at: datetime

    class Config:
        from_attributes = True


class HandleRequest(BaseModel):
    """处理预警请求"""
    action: str
    result: Optional[str] = None


class AlertRecordResponse(BaseModel):
    """预警处理记录响应"""
    id: int
    handler_name: Optional[str] = None
    action: str
    result: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ========== API 端点 ==========

@router.get("", response_model=dict, summary="获取预警列表")
def get_alerts(
    page: int = 1,
    page_size: int = 20,
    status: Optional[AlertStatus] = None,
    level: Optional[AlertLevel] = None,
    class_id: Optional[int] = None,
    student_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取预警列表

    权限控制：
    - admin: 可以查看所有预警
    - counselor: 只能查看其管理班级学生的预警
    - student: 只能查看自己的预警
    """
    # 基础查询（join Student 表用于过滤）
    query = db.query(Alert).join(Student, Alert.student_id == Student.id)

    # ========== 核心权限过滤 ==========
    # 根据用户角色应用学生过滤
    query = apply_student_filter(query, current_user, Alert.student_id)

    # ========== 业务过滤条件 ==========
    if status:
        query = query.filter(Alert.status == status)

    if level:
        query = query.filter(Alert.level == level)

    # 班级过滤（需要检查权限）
    if class_id:
        # 检查用户是否有权限访问该班级
        if current_user.role == UserRole.COUNSELOR:
            managed_ids = current_user.get_managed_class_ids()
            if class_id not in managed_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您没有权限访问该班级的预警"
                )
        query = query.filter(Student.class_id == class_id)

    if student_name:
        query = query.filter(Student.name.like(f"%{student_name}%"))

    # 统计和分页
    total = query.count()
    alerts = query.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for a in alerts:
        items.append({
            "id": a.id,
            "student_id": a.student_id,
            "student_name": a.student.name if a.student else None,
            "student_no": a.student.student_no if a.student else None,
            "class_name": a.student.class_info.name if a.student and a.student.class_info else None,
            "rule_id": a.rule_id,
            "rule_name": a.rule.name if a.rule else None,
            "rule_type": a.rule.type.value if a.rule else None,
            "level": a.level,
            "message": a.message,
            "status": a.status,
            "created_at": a.created_at
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/statistics", summary="获取预警统计")
def get_alert_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取预警统计数据

    权限控制：
    - admin: 统计所有预警
    - counselor: 只统计其管理班级学生的预警
    - student: 只统计自己的预警
    """
    # 基础查询
    query = db.query(Alert).join(Student, Alert.student_id == Student.id)

    # ========== 核心权限过滤 ==========
    query = apply_student_filter(query, current_user, Alert.student_id)

    # 统计
    total = query.count()
    pending = query.filter(Alert.status == AlertStatus.PENDING).count()
    processing = query.filter(Alert.status == AlertStatus.PROCESSING).count()
    resolved = query.filter(Alert.status == AlertStatus.RESOLVED).count()
    ignored = query.filter(Alert.status == AlertStatus.IGNORED).count()

    # 按级别统计
    warning_count = query.filter(Alert.level == AlertLevel.WARNING).count()
    serious_count = query.filter(Alert.level == AlertLevel.SERIOUS).count()
    urgent_count = query.filter(Alert.level == AlertLevel.URGENT).count()

    return {
        "total": total,
        "by_status": {
            "pending": pending,
            "processing": processing,
            "resolved": resolved,
            "ignored": ignored
        },
        "by_level": {
            "warning": warning_count,
            "serious": serious_count,
            "urgent": urgent_count
        }
    }


@router.get("/{alert_id}", response_model=dict, summary="获取预警详情")
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取预警详情

    权限控制：
    - admin: 可以查看所有预警
    - counselor: 只能查看其管理班级学生的预警
    - student: 只能查看自己的预警
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警不存在"
        )

    # ========== 权限检查 ==========
    if not check_student_access(current_user, alert.student_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限查看该预警"
        )

    # 获取处理记录
    records = []
    for r in alert.records:
        records.append({
            "id": r.id,
            "handler_name": r.handler.student.name if r.handler and r.handler.student else r.handler.username,
            "action": r.action,
            "result": r.result,
            "created_at": r.created_at
        })

    return {
        "id": alert.id,
        "student": {
            "id": alert.student.id,
            "student_no": alert.student.student_no,
            "name": alert.student.name,
            "class_name": alert.student.class_info.name if alert.student.class_info else None,
            "phone": alert.student.phone,
            "email": alert.student.email
        } if alert.student else None,
        "rule": {
            "id": alert.rule.id,
            "name": alert.rule.name,
            "code": alert.rule.code,
            "type": alert.rule.type.value,
            "level": alert.rule.level.value,
            "description": alert.rule.description,
            "conditions": alert.rule.conditions,
            "message_template": alert.rule.message_template
        } if alert.rule else None,
        "level": alert.level,
        "message": alert.message,
        "status": alert.status,
        "created_at": alert.created_at,
        "records": records
    }


@router.post("/{alert_id}/handle", summary="处理预警")
def handle_alert(
    alert_id: int,
    data: HandleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin)
):
    """
    处理预警（记录处理信息）

    权限控制：
    - admin: 可以处理所有预警
    - counselor: 只能处理其管理班级学生的预警
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警不存在"
        )

    # ========== 权限检查 ==========
    if current_user.role == UserRole.COUNSELOR:
        if not check_student_access(current_user, alert.student_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限处理该预警"
            )

    # 创建处理记录
    record = AlertRecord(
        alert_id=alert_id,
        handler_id=current_user.id,
        action=data.action,
        result=data.result
    )
    db.add(record)

    # 更新预警状态
    if alert.status == AlertStatus.PENDING:
        alert.status = AlertStatus.PROCESSING

    db.commit()

    return {"message": "处理记录已保存", "record_id": record.id}


@router.put("/{alert_id}/status", summary="更新预警状态")
def update_alert_status(
    alert_id: int,
    status: AlertStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin)
):
    """
    更新预警状态

    权限控制：
    - admin: 可以更新所有预警状态
    - counselor: 只能更新其管理班级学生的预警状态
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警不存在"
        )

    # ========== 权限检查 ==========
    if current_user.role == UserRole.COUNSELOR:
        if not check_student_access(current_user, alert.student_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限更新该预警状态"
            )

    alert.status = status
    db.commit()

    return {"message": "状态更新成功"}


@router.post("/{alert_id}/resolve", summary="解决预警")
def resolve_alert(
    alert_id: int,
    result: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin)
):
    """
    解决预警

    权限控制：
    - admin: 可以解决所有预警
    - counselor: 只能解决其管理班级学生的预警
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警不存在"
        )

    # ========== 权限检查 ==========
    if current_user.role == UserRole.COUNSELOR:
        if not check_student_access(current_user, alert.student_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限解决该预警"
            )

    # 创建处理记录
    record = AlertRecord(
        alert_id=alert_id,
        handler_id=current_user.id,
        action="resolve",
        result=result or "预警已解决"
    )
    db.add(record)

    # 更新预警状态
    alert.status = AlertStatus.RESOLVED

    db.commit()

    return {"message": "预警已标记为已解决"}


@router.post("/{alert_id}/ignore", summary="忽略预警")
def ignore_alert(
    alert_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin)
):
    """
    忽略预警

    权限控制：
    - admin: 可以忽略所有预警
    - counselor: 只能忽略其管理班级学生的预警
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警不存在"
        )

    # ========== 权限检查 ==========
    if current_user.role == UserRole.COUNSELOR:
        if not check_student_access(current_user, alert.student_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限忽略该预警"
            )

    # 创建处理记录
    record = AlertRecord(
        alert_id=alert_id,
        handler_id=current_user.id,
        action="ignore",
        result=reason or "预警已忽略"
    )
    db.add(record)

    # 更新预警状态
    alert.status = AlertStatus.IGNORED

    db.commit()

    return {"message": "预警已忽略"}


@router.get("/by-class/{class_id}", summary="获取指定班级的预警")
def get_alerts_by_class(
    class_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定班级的预警列表

    权限控制：
    - admin: 可以查看所有班级的预警
    - counselor: 只能查看其管理班级的预警
    - student: 返回空列表
    """
    # ========== 权限检查 ==========
    if current_user.role == UserRole.COUNSELOR:
        managed_ids = current_user.get_managed_class_ids()
        if class_id not in managed_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限访问该班级的预警"
            )
    elif current_user.role == UserRole.STUDENT:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    # 查询该班级学生的预警
    query = db.query(Alert).join(Student).filter(Student.class_id == class_id)

    total = query.count()
    alerts = query.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for a in alerts:
        items.append({
            "id": a.id,
            "student_id": a.student_id,
            "student_name": a.student.name if a.student else None,
            "student_no": a.student.student_no if a.student else None,
            "class_name": a.student.class_info.name if a.student and a.student.class_info else None,
            "rule_id": a.rule_id,
            "rule_name": a.rule.name if a.rule else None,
            "rule_type": a.rule.type.value if a.rule else None,
            "level": a.level,
            "message": a.message,
            "status": a.status,
            "created_at": a.created_at
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }
