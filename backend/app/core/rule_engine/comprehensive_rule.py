"""Comprehensive academic risk evaluation."""
from __future__ import annotations

from typing import Any, Optional

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
    records = (
        db_session.query(Score)
        .filter(Score.student_id == student_id)
        .order_by(
            Score.semester.asc(),
            Score.course_id.asc(),
            Score.updated_at.desc(),
            Score.created_at.desc(),
            Score.id.desc(),
        )
        .all()
    )

    semester_course_latest: dict[tuple[str, int], Score] = {}
    for record in records:
        semester_key = record.semester or ""
        course_key = record.course_id or 0
        key = (semester_key, course_key)
        if key not in semester_course_latest:
            semester_course_latest[key] = record

    semester_fail_counts: dict[str, int] = {}
    for (semester, _), record in semester_course_latest.items():
        if record.score is not None and float(record.score) < 60:
            semester_fail_counts[semester] = semester_fail_counts.get(semester, 0) + 1

    target_semester: Optional[str] = None
    fail_count = 0
    for semester, count in semester_fail_counts.items():
        if count > fail_count or (count == fail_count and semester > (target_semester or "")):
            target_semester = semester or None
            fail_count = count

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


def _get_active_alerts(db_session: Session, student_id: int, rule_id: int) -> list[Alert]:
    return (
        db_session.query(Alert)
        .filter(
            Alert.student_id == student_id,
            Alert.rule_id == rule_id,
            Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING]),
        )
        .order_by(Alert.id.asc())
        .all()
    )


def evaluate_comprehensive_rule(
    student_id: int,
    db_session: Session,
    rule: Optional[Rule] = None,
) -> dict[str, Any]:
    """Evaluate the cross-source comprehensive rule and synchronize alert state."""
    student = db_session.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {
            "triggered": False,
            "alert_created": False,
            "alert_resolved": 0,
            "student_id": student_id,
            "message": "student_not_found",
        }

    rule = rule or ensure_comprehensive_rule(db_session)
    conditions = rule.conditions if isinstance(rule.conditions, dict) else {}
    fail_threshold = int(conditions.get("fail_count_threshold", conditions.get("threshold", DEFAULT_FAIL_THRESHOLD)))
    absence_threshold = int(conditions.get("absence_count_threshold", DEFAULT_ABSENCE_THRESHOLD))

    semester, fail_count = _pick_semester_fail_count(db_session, student_id)
    absence_count = int(
        db_session.query(Attendance)
        .filter(
            Attendance.student_id == student_id,
            Attendance.status == AttendanceStatus.ABSENT,
        )
        .count()
        or 0
    )

    triggered = fail_count >= fail_threshold and absence_count >= absence_threshold
    message = _build_message(rule, fail_count, absence_count)

    alert_created = False
    alert_resolved = 0
    alert_id: Optional[int] = None
    active_alerts = _get_active_alerts(db_session, student_id, rule.id)

    if triggered:
        if active_alerts:
            primary_alert = active_alerts[0]
            primary_alert.level = rule.level
            primary_alert.message = message
            primary_alert.semester = semester
            alert_id = primary_alert.id
            for duplicate in active_alerts[1:]:
                duplicate.status = AlertStatus.RESOLVED
                alert_resolved += 1
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
    else:
        for active_alert in active_alerts:
            active_alert.status = AlertStatus.RESOLVED
            alert_resolved += 1

    return {
        "triggered": triggered,
        "alert_created": alert_created,
        "alert_resolved": alert_resolved,
        "alert_id": alert_id,
        "student_id": student_id,
        "student_name": student.name,
        "student_no": student.student_no,
        "semester": semester,
        "fail_count": fail_count,
        "absence_count": absence_count,
        "message": message,
    }
