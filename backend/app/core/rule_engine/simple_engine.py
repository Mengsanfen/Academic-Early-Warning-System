from __future__ import annotations

"""Lightweight academic rule engine."""

import logging
import operator
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.rule_engine.comprehensive_rule import (
    ensure_comprehensive_rule,
    evaluate_comprehensive_rule,
)
from app.models.rule import COMPREHENSIVE_RULE_CODE, COMPREHENSIVE_RULE_MODE, TargetType

logger = logging.getLogger(__name__)


class RuleEngineError(Exception):
    """Custom rule engine error."""


class SimpleRuleEngine:
    """Evaluate active rules and synchronize alert state."""

    OPERATORS = {
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
        "==": operator.eq,
        "!=": operator.ne,
        "lt": operator.lt,
        "le": operator.le,
        "gt": operator.gt,
        "ge": operator.ge,
        "eq": operator.eq,
        "ne": operator.ne,
    }

    METRIC_TYPES = {
        "score",
        "avg_score",
        "fail_count",
        "gpa",
        "earned_credit",
        "failed_credit",
        "attendance_rate",
        "absence_count",
        "late_count",
    }

    COURSE_TYPES = {"required", "elective", "public", "professional", "practice"}

    def __init__(self, db: Session):
        self.db = db

    def execute_all_rules(self) -> Dict[str, Any]:
        """Execute all active rules against their scoped students."""
        from app.models.rule import Rule

        stats = {
            "total_students": 0,
            "total_rules": 0,
            "total_checked": 0,
            "total_triggered": 0,
            "alerts_created": 0,
            "alerts_resolved": 0,
            "errors": [],
            "rule_details": [],
        }

        try:
            ensure_comprehensive_rule(self.db)
            rules = self.db.query(Rule).filter(Rule.is_active == True).all()
            if not rules:
                logger.warning("No active rules found")
                return stats

            stats["total_rules"] = len(rules)
            for rule in rules:
                stats["rule_details"].append(self._execute_single_rule(rule, stats))

            self.db.commit()
            logger.info(
                "Rule execution finished: checked=%s triggered=%s created=%s resolved=%s",
                stats["total_checked"],
                stats["total_triggered"],
                stats["alerts_created"],
                stats["alerts_resolved"],
            )
        except Exception as exc:
            self.db.rollback()
            error_msg = f"Rule engine execution failed: {exc}"
            logger.exception(error_msg)
            stats["errors"].append(error_msg)

        return stats

    def _get_target_students(self, rule: Any) -> List[Any]:
        from app.models.student import Class, Student

        query = self.db.query(Student).filter(Student.is_active == True)
        target_type = rule.target_type or TargetType.ALL

        if target_type == TargetType.GRADES:
            if rule.target_grades and isinstance(rule.target_grades, list):
                query = query.join(Class).filter(Class.grade.in_(rule.target_grades))
        elif target_type == TargetType.CLASSES:
            if rule.target_classes and isinstance(rule.target_classes, list):
                query = query.filter(Student.class_id.in_(rule.target_classes))

        return query.all()

    def _execute_single_rule(self, rule: Any, stats: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "rule_code": rule.code,
            "triggered_count": 0,
            "alerts_created": 0,
            "alerts_resolved": 0,
            "error": None,
        }

        try:
            students = self._get_target_students(rule)
            if not students:
                logger.warning("Rule %s has no target students", rule.id)
                return result

            stats["total_students"] = max(stats["total_students"], len(students))
            stats["total_checked"] += len(students)

            conditions = self._parse_conditions(rule.conditions)
            if conditions is None:
                result["error"] = "rule_condition_parse_failed"
                return result

            if rule.code == COMPREHENSIVE_RULE_CODE or conditions.get("mode") == COMPREHENSIVE_RULE_MODE:
                for student in students:
                    try:
                        evaluation = evaluate_comprehensive_rule(student.id, self.db, rule)
                        if evaluation.get("triggered"):
                            stats["total_triggered"] += 1
                            result["triggered_count"] += 1
                        if evaluation.get("alert_created"):
                            stats["alerts_created"] += 1
                            result["alerts_created"] += 1
                        if evaluation.get("alert_resolved"):
                            resolved_count = int(evaluation["alert_resolved"])
                            stats["alerts_resolved"] += resolved_count
                            result["alerts_resolved"] += resolved_count
                    except Exception as exc:
                        logger.warning(
                            "Failed to evaluate comprehensive rule %s for student %s: %s",
                            rule.id,
                            student.id,
                            exc,
                        )
                return result

            metric_type = conditions.get("metric")
            threshold = conditions.get("threshold")
            op_str = conditions.get("operator", "<")
            time_window = conditions.get("time_window")
            course_type = conditions.get("course_type")

            if metric_type is None or threshold is None:
                result["error"] = f"missing_required_fields: metric={metric_type}, threshold={threshold}"
                return result

            op_func = self.OPERATORS.get(op_str)
            if op_func is None:
                result["error"] = f"unsupported_operator: {op_str}"
                return result

            for student in students:
                try:
                    metric_value = self._calculate_metric(student.id, metric_type, time_window, course_type)
                    if metric_value is None:
                        continue

                    if op_func(metric_value, threshold):
                        stats["total_triggered"] += 1
                        result["triggered_count"] += 1
                        message = self._generate_message(rule, student, metric_value, threshold)
                        _, created, dedup_resolved = self._upsert_active_alert(rule, student, message)
                        if created:
                            stats["alerts_created"] += 1
                            result["alerts_created"] += 1
                        if dedup_resolved:
                            stats["alerts_resolved"] += dedup_resolved
                            result["alerts_resolved"] += dedup_resolved
                    else:
                        resolved_count = self._resolve_active_alerts(rule.id, student.id)
                        if resolved_count:
                            stats["alerts_resolved"] += resolved_count
                            result["alerts_resolved"] += resolved_count
                except Exception as exc:
                    logger.warning(
                        "Failed to evaluate rule %s for student %s: %s",
                        rule.id,
                        student.id,
                        exc,
                    )
        except Exception as exc:
            error_msg = f"Rule {rule.id} execution failed: {exc}"
            logger.exception(error_msg)
            result["error"] = error_msg
            stats["errors"].append(error_msg)

        return result

    def _get_active_alerts(self, rule_id: int, student_id: int) -> List[Any]:
        from app.models.alert import Alert, AlertStatus

        return (
            self.db.query(Alert)
            .filter(
                Alert.student_id == student_id,
                Alert.rule_id == rule_id,
                Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING]),
            )
            .order_by(Alert.id.asc())
            .all()
        )

    def _upsert_active_alert(self, rule: Any, student: Any, message: str) -> Tuple[Any, bool, int]:
        from app.models.alert import Alert, AlertStatus

        active_alerts = self._get_active_alerts(rule.id, student.id)
        if active_alerts:
            primary_alert = active_alerts[0]
            primary_alert.level = rule.level
            primary_alert.message = message
            resolved_duplicates = 0
            for duplicate in active_alerts[1:]:
                if duplicate.status != AlertStatus.RESOLVED:
                    duplicate.status = AlertStatus.RESOLVED
                    resolved_duplicates += 1
            return primary_alert, False, resolved_duplicates

        alert = Alert(
            student_id=student.id,
            rule_id=rule.id,
            level=rule.level,
            message=message,
            status=AlertStatus.PENDING,
        )
        self.db.add(alert)
        return alert, True, 0

    def _resolve_active_alerts(self, rule_id: int, student_id: int) -> int:
        from app.models.alert import AlertStatus

        active_alerts = self._get_active_alerts(rule_id, student_id)
        for alert in active_alerts:
            alert.status = AlertStatus.RESOLVED
        return len(active_alerts)

    def _parse_conditions(self, conditions: Any) -> Optional[Dict[str, Any]]:
        import json

        if conditions is None:
            return None

        try:
            if isinstance(conditions, dict):
                return conditions
            if isinstance(conditions, str):
                return json.loads(conditions)
            logger.warning("Unknown condition type: %s", type(conditions))
            return None
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode rule conditions JSON: %s", exc)
            return None
        except Exception as exc:
            logger.error("Failed to parse rule conditions: %s", exc)
            return None

    def _calculate_metric(
        self,
        student_id: int,
        metric_type: str,
        time_window: Optional[str] = None,
        course_type: Optional[str] = None,
    ) -> Optional[float]:
        try:
            start_date = self._parse_time_window(time_window)

            if metric_type == "score":
                return self._calc_latest_score(student_id, start_date, course_type)
            if metric_type == "avg_score":
                return self._calc_avg_score(student_id, start_date, course_type)
            if metric_type == "fail_count":
                return self._calc_fail_count(student_id, start_date, course_type)
            if metric_type == "gpa":
                return self._calc_gpa(student_id, start_date, course_type)
            if metric_type == "earned_credit":
                return self._calc_earned_credit(student_id, start_date, course_type)
            if metric_type == "failed_credit":
                return self._calc_failed_credit(student_id, start_date, course_type)
            if metric_type == "attendance_rate":
                return self._calc_attendance_rate(student_id, start_date, course_type)
            if metric_type == "absence_count":
                return self._calc_absence_count(student_id, start_date, course_type)
            if metric_type == "late_count":
                return self._calc_late_count(student_id, start_date, course_type)

            logger.warning("Unknown metric type: %s", metric_type)
            return None
        except Exception as exc:
            logger.error("Failed to calculate metric %s for student %s: %s", metric_type, student_id, exc)
            return None

    def _parse_time_window(self, time_window: Optional[str]) -> Optional[datetime]:
        if not time_window:
            return None

        now = datetime.now()
        window_map = {
            "1w": timedelta(weeks=1),
            "2w": timedelta(weeks=2),
            "1m": timedelta(days=30),
            "3m": timedelta(days=90),
            "1term": timedelta(days=150),
            "1y": timedelta(days=365),
            "1周": timedelta(weeks=1),
            "2周": timedelta(weeks=2),
            "1个月": timedelta(days=30),
            "3个月": timedelta(days=90),
            "1学期": timedelta(days=150),
            "1学年": timedelta(days=365),
            "本学期": timedelta(days=150),
        }
        delta = window_map.get(time_window)
        return now - delta if delta else None

    def _get_score_records(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> List[Any]:
        from app.models.course import Course, CourseType
        from app.models.score import Score

        query = self.db.query(Score).join(Course, Score.course_id == Course.id).filter(Score.student_id == student_id)

        if start_date:
            query = query.filter(Score.updated_at >= start_date)

        if course_type:
            try:
                query = query.filter(Course.course_type == CourseType(course_type))
            except ValueError:
                logger.warning("Unknown course type: %s", course_type)
                return []

        return (
            query.order_by(
                Score.course_id.asc(),
                Score.updated_at.desc(),
                Score.created_at.desc(),
                Score.id.desc(),
            ).all()
        )

    def _get_latest_scores_by_course(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> List[Any]:
        records = self._get_score_records(student_id, start_date, course_type)
        latest_records: Dict[int, Any] = {}
        for record in records:
            if record.course_id not in latest_records:
                latest_records[record.course_id] = record
        return list(latest_records.values())

    def _calc_latest_score(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> Optional[float]:
        try:
            latest_scores = self._get_latest_scores_by_course(student_id, start_date, course_type)
            valid_scores = [float(score.score) for score in latest_scores if score.score is not None]
            if not valid_scores:
                return None
            return min(valid_scores)
        except Exception as exc:
            logger.error("Failed to query current score for student %s: %s", student_id, exc)
            return None

    def _calc_avg_score(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> Optional[float]:
        try:
            scores = [
                score for score in self._get_latest_scores_by_course(student_id, start_date, course_type)
                if score.score is not None
            ]
            if not scores:
                return None
            total = sum(float(item.score) for item in scores)
            return round(total / len(scores), 2)
        except Exception as exc:
            logger.error("Failed to calculate average score: %s", exc)
            return None

    def _calc_fail_count(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> int:
        try:
            latest_scores = self._get_latest_scores_by_course(student_id, start_date, course_type)
            return sum(1 for score in latest_scores if score.score is not None and float(score.score) < 60)
        except Exception as exc:
            logger.error("Failed to calculate fail count: %s", exc)
            return 0

    def _calc_gpa(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> float:
        try:
            scores = self._get_latest_scores_by_course(student_id, start_date, course_type)
            if not scores:
                return 0.0

            total_credits = 0.0
            total_points = 0.0
            for score in scores:
                if score.score is None:
                    continue
                credit = float(score.course.credit) if score.course and score.course.credit else 1.0
                total_credits += credit
                total_points += self._score_to_gpa(float(score.score)) * credit

            if total_credits == 0:
                return 0.0
            return round(total_points / total_credits, 2)
        except Exception as exc:
            logger.error("Failed to calculate GPA: %s", exc)
            return 0.0

    def _calc_earned_credit(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> float:
        try:
            scores = self._get_latest_scores_by_course(student_id, start_date, course_type)
            total = sum(
                float(score.course.credit)
                for score in scores
                if score.course and score.score is not None and float(score.score) >= 60
            )
            return round(total, 2)
        except Exception as exc:
            logger.error("Failed to calculate earned credits: %s", exc)
            return 0.0

    def _calc_failed_credit(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> float:
        try:
            scores = self._get_latest_scores_by_course(student_id, start_date, course_type)
            total = sum(
                float(score.course.credit)
                for score in scores
                if score.course and score.score is not None and float(score.score) < 60
            )
            return round(total, 2)
        except Exception as exc:
            logger.error("Failed to calculate failed credits: %s", exc)
            return 0.0

    def _score_to_gpa(self, score: float) -> float:
        if score >= 90:
            return 4.0
        if score >= 85:
            return 3.7
        if score >= 82:
            return 3.3
        if score >= 78:
            return 3.0
        if score >= 75:
            return 2.7
        if score >= 72:
            return 2.3
        if score >= 68:
            return 2.0
        if score >= 64:
            return 1.5
        if score >= 60:
            return 1.0
        return 0.0

    def _calc_attendance_rate(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> float:
        from app.models.attendance import Attendance, AttendanceStatus
        from app.models.course import Course, CourseType

        try:
            query = self.db.query(Attendance).join(Course, Attendance.course_id == Course.id).filter(
                Attendance.student_id == student_id
            )

            if start_date:
                query = query.filter(Attendance.date >= start_date.date())

            if course_type:
                try:
                    query = query.filter(Course.course_type == CourseType(course_type))
                except ValueError:
                    logger.warning("Unknown course type: %s", course_type)

            attendances = query.all()
            if not attendances:
                return 1.0

            present_count = sum(1 for item in attendances if item.status == AttendanceStatus.PRESENT)
            return round(present_count / len(attendances), 4)
        except Exception as exc:
            logger.error("Failed to calculate attendance rate: %s", exc)
            return 1.0

    def _calc_absence_count(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> int:
        from app.models.attendance import Attendance, AttendanceStatus
        from app.models.course import Course, CourseType

        try:
            query = self.db.query(Attendance).join(Course, Attendance.course_id == Course.id).filter(
                Attendance.student_id == student_id,
                Attendance.status == AttendanceStatus.ABSENT,
            )

            if start_date:
                query = query.filter(Attendance.date >= start_date.date())

            if course_type:
                try:
                    query = query.filter(Course.course_type == CourseType(course_type))
                except ValueError:
                    logger.warning("Unknown course type: %s", course_type)

            return query.count()
        except Exception as exc:
            logger.error("Failed to calculate absence count: %s", exc)
            return 0

    def _calc_late_count(
        self,
        student_id: int,
        start_date: Optional[datetime],
        course_type: Optional[str] = None,
    ) -> int:
        from app.models.attendance import Attendance, AttendanceStatus
        from app.models.course import Course, CourseType

        try:
            query = self.db.query(Attendance).join(Course, Attendance.course_id == Course.id).filter(
                Attendance.student_id == student_id,
                Attendance.status == AttendanceStatus.LATE,
            )

            if start_date:
                query = query.filter(Attendance.date >= start_date.date())

            if course_type:
                try:
                    query = query.filter(Course.course_type == CourseType(course_type))
                except ValueError:
                    logger.warning("Unknown course type: %s", course_type)

            return query.count()
        except Exception as exc:
            logger.error("Failed to calculate late count: %s", exc)
            return 0

    def _generate_message(self, rule: Any, student: Any, metric_value: float, threshold: float) -> str:
        try:
            if rule.message_template:
                return rule.message_template.format(
                    student_name=student.name,
                    student_no=student.student_no,
                    metric_value=metric_value,
                    threshold=threshold,
                    rule_name=rule.name,
                )
            return (
                f"学生{student.name}({student.student_no})触发预警：{rule.name}，"
                f"当前值 {metric_value}，阈值 {threshold}"
            )
        except Exception as exc:
            logger.warning("Failed to render alert message: %s", exc)
            return f"学生{student.name}({student.student_no})触发预警：{rule.name}"



def run_rule_detection(db: Session) -> Dict[str, Any]:
    engine = SimpleRuleEngine(db)
    return engine.execute_all_rules()
