"""
Dashboard APIs with counselor class scoping.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import apply_class_filter, get_counselor_or_admin
from app.database import get_db
from app.models.alert import Alert, AlertStatus
from app.models.rule import AlertLevel, Rule, RuleType
from app.models.student import Class, Student
from app.models.user import User


router = APIRouter()


def _validate_days(days: int) -> int:
    if days < 1 or days > 90:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="days 必须在 1 到 90 之间",
        )
    return days


def _scoped_student_query(db: Session, current_user: User):
    query = db.query(Student)
    return apply_class_filter(query, current_user, Student.class_id)


def _scoped_alert_query(db: Session, current_user: User):
    query = db.query(Alert).join(Student, Alert.student_id == Student.id)
    return apply_class_filter(query, current_user, Student.class_id)


@router.get("/overview", summary="获取仪表盘概览数据")
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    student_count = _scoped_student_query(db, current_user).count()

    alert_query = _scoped_alert_query(db, current_user)
    alert_total = alert_query.count()
    alert_pending = alert_query.filter(Alert.status == AlertStatus.PENDING).count()
    alert_processing = alert_query.filter(Alert.status == AlertStatus.PROCESSING).count()
    alert_resolved = alert_query.filter(Alert.status == AlertStatus.RESOLVED).count()

    alert_by_level = {
        level.value: alert_query.filter(Alert.level == level).count()
        for level in AlertLevel
    }

    alert_by_type = {
        rule_type.value: (
            alert_query.join(Rule, Alert.rule_id == Rule.id).filter(Rule.type == rule_type).count()
        )
        for rule_type in RuleType
    }

    recent_alerts = (
        _scoped_alert_query(db, current_user)
        .options(joinedload(Alert.student).joinedload(Student.class_info), joinedload(Alert.rule))
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(10)
        .all()
    )

    return {
        "student_count": student_count,
        "alert_count": {
            "total": alert_total,
            "pending": alert_pending,
            "processing": alert_processing,
            "resolved": alert_resolved,
        },
        "alert_by_level": alert_by_level,
        "alert_by_type": alert_by_type,
        "recent_alerts": [
            {
                "id": alert.id,
                "student_name": alert.student.name if alert.student else None,
                "student_no": alert.student.student_no if alert.student else None,
                "class_name": (
                    alert.student.class_info.name
                    if alert.student and alert.student.class_info
                    else None
                ),
                "rule_name": alert.rule.name if alert.rule else None,
                "level": alert.level.value if alert.level else None,
                "status": alert.status.value if alert.status else None,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            }
            for alert in recent_alerts
        ],
    }


@router.get("/trend", summary="获取预警趋势数据")
def get_trend(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    days = _validate_days(days)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days - 1)
    alert_query = _scoped_alert_query(db, current_user)

    trend_data = []
    for offset in range(days):
        date = start_date + timedelta(days=offset)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        count = alert_query.filter(
            Alert.created_at >= date_start,
            Alert.created_at <= date_end,
        ).count()
        trend_data.append({"date": date.strftime("%Y-%m-%d"), "count": count})

    return {"days": days, "data": trend_data}


@router.get("/distribution", summary="获取预警分布数据")
def get_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin),
):
    scoped_alert_query = _scoped_alert_query(db, current_user)

    class_distribution = (
        scoped_alert_query.with_entities(
            Class.name.label("class_name"),
            func.count(Alert.id).label("count"),
        )
        .join(Class, Student.class_id == Class.id)
        .group_by(Class.id, Class.name)
        .order_by(func.count(Alert.id).desc(), Class.id.asc())
        .all()
    )

    type_rows = (
        scoped_alert_query.with_entities(
            Rule.type.label("rule_type"),
            func.count(Alert.id).label("count"),
        )
        .join(Rule, Alert.rule_id == Rule.id)
        .group_by(Rule.type)
        .all()
    )
    type_map = {
        row.rule_type.value if row.rule_type else "unknown": row.count
        for row in type_rows
    }

    return {
        "by_class": [
            {"class_name": row.class_name, "count": row.count}
            for row in class_distribution
        ],
        "by_type": [
            {"type": rule_type.value, "count": type_map.get(rule_type.value, 0)}
            for rule_type in RuleType
        ],
    }
