"""
Comprehensive academic risk evaluation.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.models.rule import (
    AlertLevel,
    COMPREHENSIVE_RULE_CODE,
    COMPREHENSIVE_RULE_MODE,
    Rule,
    RuleType,
)
from app.models.score import Score
from app.models.student import Student


DEFAULT_FAIL_THRESHOLD = 2
DEFAULT_ABSENCE_THRESHOLD = 3


def ensure_comprehensive_rule(db_session: Session) -> Rule:
    rule = db_session.query(Rule).filter(Rule.code == COMPREHENSIVE_RULE_CODE).first()
    if rule:
        return rule

    rule = Rule(
        name="学业综合风险预警",
        code=COMPREHENSIVE_RULE_CODE,
        type=RuleType.GRADUATION,
        conditions={
            "mode": COMPREHENSIVE_RULE_MODE,
            "fail_count_threshold": DEFAULT_FAIL_THRESHOLD,
            "absence_count_threshold": DEFAULT_ABSENCE_THRESHOLD,
        },
        level=AlertLevel.URGENT,
        description="单学期不及格课程数达到 2 门且累计缺勤次数达到 3 次",
        message_template="综合风险：该生已挂科 {fail_count} 门，且缺勤 {absence_count} 次，请立即干预！",
        is_active=True,
    )
    db_session.add(rule)
    db_session.flush()
    return rule


def _pick_semester_fail_count(db_session: Session, student_id: int) -> tuple[Optional[str], int]:
    semester_rows = (
        db_session.query(
            Score.semester,
            func.count(Score.id).label("fail_count"),
        )
        .filter(Score.student_id == student_id, Score.score < 60)
        .group_by(Score.semester)
        .all()
    )

    target_semester: Optional[str] = None
    fail_count = 0

    for semester, count in semester_rows:
        current_semester = semester or ""
        current_count = int(count or 0)
        if current_count > fail_count or (
            current_count == fail_count and current_semester > (target_semester or "")
        ):
            target_semester = semester
            fail_count = current_count

    return target_semester, fail_count


def _build_message(rule: Rule, fail_count: int, absence_count: int) -> str:
    if rule.message_template:
        try:
            return rule.message_template.format(
                fail_count=fail_count,
                absence_count=absence_count,
            )
        except Exception:
            pass
    return f"综合风险：该生已挂科 {fail_count} 门，且缺勤 {absence_count} 次，请立即干预！"


def evaluate_comprehensive_rule(
    student_id: int,
    db_session: Session,
    rule: Optional[Rule] = None,
) -> dict[str, Any]:
    """
    Evaluate the cross-source comprehensive rule and create/update the alert.

    The caller is responsible for committing the session.
    """
    student = db_session.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {
            "triggered": False,
            "alert_created": False,
            "student_id": student_id,
            "message": "student_not_found",
        }

    rule = rule or ensure_comprehensive_rule(db_session)
    conditions = rule.conditions if isinstance(rule.conditions, dict) else {}
    fail_threshold = int(conditions.get("fail_count_threshold", conditions.get("threshold", DEFAULT_FAIL_THRESHOLD)))
    absence_threshold = int(conditions.get("absence_count_threshold", DEFAULT_ABSENCE_THRESHOLD))

    semester, fail_count = _pick_semester_fail_count(db_session, student_id)
    absence_count = int(
        db_session.query(func.count(Attendance.id))
        .filter(
            Attendance.student_id == student_id,
            Attendance.status == AttendanceStatus.ABSENT,
        )
        .scalar()
        or 0
    )

    triggered = fail_count >= fail_threshold and absence_count >= absence_threshold
    message = _build_message(rule, fail_count, absence_count)

    alert_created = False
    alert_id: Optional[int] = None

    if triggered:
        existing = (
            db_session.query(Alert)
            .filter(
                Alert.student_id == student_id,
                Alert.rule_id == rule.id,
                Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING]),
            )
            .first()
        )

        if existing:
            existing.level = rule.level
            existing.message = message
            existing.semester = semester
            alert_id = existing.id
        else:
            alert = Alert(
                student_id=student_id,
                rule_id=rule.id,
                level=AlertLevel.URGENT,
                message=message,
                status=AlertStatus.PENDING,
                semester=semester,
            )
            db_session.add(alert)
            db_session.flush()
            alert_created = True
            alert_id = alert.id

    return {
        "triggered": triggered,
        "alert_created": alert_created,
        "alert_id": alert_id,
        "student_id": student_id,
        "student_name": student.name,
        "student_no": student.student_no,
        "semester": semester,
        "fail_count": fail_count,
        "absence_count": absence_count,
        "message": message,
    }
