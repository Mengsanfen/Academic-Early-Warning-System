"""
仪表盘 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.student import Student
from app.models.alert import Alert, AlertStatus
from app.models.rule import AlertLevel, RuleType


router = APIRouter()


@router.get("/overview", summary="获取仪表盘概览数据")
def get_overview(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取仪表盘概览数据"""
    # 学生总数
    student_count = db.query(Student).count()

    # 预警统计
    alert_total = db.query(Alert).count()
    alert_pending = db.query(Alert).filter(Alert.status == AlertStatus.PENDING).count()
    alert_processing = db.query(Alert).filter(Alert.status == AlertStatus.PROCESSING).count()
    alert_resolved = db.query(Alert).filter(Alert.status == AlertStatus.RESOLVED).count()

    # 按级别统计
    alert_by_level = {}
    for level in AlertLevel:
        count = db.query(Alert).filter(Alert.level == level).count()
        alert_by_level[level.value] = count

    # 按类型统计
    alert_by_type = {}
    for rule_type in RuleType:
        count = db.query(Alert).join(Alert.rule).filter(Alert.rule.property.mapper.class_.type == rule_type).count()
        alert_by_type[rule_type.value] = count

    # 最近预警（前10条）
    recent_alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(10).all()
    recent = []
    for a in recent_alerts:
        recent.append({
            "id": a.id,
            "student_name": a.student.name if a.student else None,
            "student_no": a.student.student_no if a.student else None,
            "rule_name": a.rule.name if a.rule else None,
            "level": a.level.value,
            "status": a.status.value,
            "created_at": a.created_at.isoformat()
        })

    return {
        "student_count": student_count,
        "alert_count": {
            "total": alert_total,
            "pending": alert_pending,
            "processing": alert_processing,
            "resolved": alert_resolved
        },
        "alert_by_level": alert_by_level,
        "alert_by_type": alert_by_type,
        "recent_alerts": recent
    }


@router.get("/trend", summary="获取预警趋势数据")
def get_trend(
    days: int = 7,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取近N天的预警趋势数据"""
    from datetime import datetime, timedelta

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 按日期统计预警数量
    trend_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        count = db.query(Alert).filter(
            Alert.created_at >= date_start,
            Alert.created_at <= date_end
        ).count()

        trend_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "count": count
        })

    return {
        "days": days,
        "data": trend_data
    }


@router.get("/distribution", summary="获取预警分布数据")
def get_distribution(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取预警分布数据（按班级、按类型等）"""
    # 按班级统计
    from sqlalchemy import func
    from app.models.student import Class

    class_distribution = db.query(
        Class.name,
        func.count(Alert.id).label('count')
    ).join(Student, Alert.student).join(Class, Student.class_info).group_by(Class.id).all()

    by_class = [{"class_name": name, "count": count} for name, count in class_distribution]

    # 按规则类型统计
    type_distribution = db.query(
        Alert.rule.property.mapper.class_.type,
        func.count(Alert.id).label('count')
    ).join(Alert.rule).group_by(Alert.rule.property.mapper.class_.type).all()

    by_type = [{"type": t.value, "count": count} for t, count in type_distribution]

    return {
        "by_class": by_class,
        "by_type": by_type
    }
