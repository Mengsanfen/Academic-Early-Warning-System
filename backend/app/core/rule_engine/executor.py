"""
规则引擎 - 规则执行器

负责将解析后的规则应用到学生数据上，计算是否触发预警
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.rule_engine.parser import RuleParser, ParsedRule
from app.core.rule_engine.operators import compare
from app.core.rule_engine.aggregators import aggregate


@dataclass
class ExecutionResult:
    """规则执行结果"""
    triggered: bool                    # 是否触发
    metric_value: Any                  # 指标计算值
    threshold: Any                     # 阈值
    details: Optional[Dict[str, Any]] = None  # 详细信息


class MetricCalculator:
    """指标计算器 - 从学生数据中计算各种指标"""

    def __init__(self, db: Session):
        self.db = db

    def calculate(self, student_id: int, metric: str,
                  time_window: Optional[str] = None,
                  extra: Optional[Dict[str, Any]] = None) -> Any:
        """
        计算学生指标值

        Args:
            student_id: 学生ID
            metric: 指标名称
            time_window: 时间窗口（如 "1个月", "1学期"）
            extra: 额外参数

        Returns:
            指标计算结果
        """
        extra = extra or {}

        # 解析时间窗口
        start_date = self._parse_time_window(time_window)

        # 根据指标类型选择计算方法
        metric_handlers = {
            "score": self._calc_score,
            "fail_count": self._calc_fail_count,
            "gpa": self._calc_gpa,
            "absence_rate": self._calc_absence_rate,
            "absence_count": self._calc_absence_count,
            "credit_ratio": self._calc_credit_ratio,
            "continuous_absence": self._calc_continuous_absence,
        }

        handler = metric_handlers.get(metric)
        if not handler:
            raise ValueError(f"未知的指标类型: {metric}")

        return handler(student_id, start_date, extra)

    def _parse_time_window(self, time_window: Optional[str]) -> Optional[datetime]:
        """解析时间窗口为起始日期"""
        if not time_window:
            return None

        now = datetime.now()

        # 时间窗口映射
        window_map = {
            "1周": timedelta(weeks=1),
            "2周": timedelta(weeks=2),
            "1个月": timedelta(days=30),
            "3个月": timedelta(days=90),
            "1学期": timedelta(days=150),
            "1学年": timedelta(days=365),
        }

        delta = window_map.get(time_window)
        if delta:
            return now - delta

        return None

    def _calc_score(self, student_id: int, start_date: Optional[datetime],
                    extra: Dict[str, Any]) -> Optional[float]:
        """计算成绩相关指标"""
        from app.models.score import Score

        query = self.db.query(Score).filter(Score.student_id == student_id)

        # 应用时间过滤
        if start_date:
            query = query.filter(Score.created_at >= start_date)

        # 课程过滤
        course_id = extra.get("course_id")
        if course_id:
            query = query.filter(Score.course_id == course_id)

        scores = query.all()

        if not scores:
            return None

        # 返回指定成绩类型
        score_type = extra.get("score_type", "total")
        if score_type == "avg":
            # 平均成绩
            score_values = [float(s.score) for s in scores if s.score is not None]
            return sum(score_values) / len(score_values) if score_values else None

        # 默认返回最新一条成绩
        return float(scores[0].score) if scores else None

    def _calc_fail_count(self, student_id: int, start_date: Optional[datetime],
                         extra: Dict[str, Any]) -> int:
        """计算挂科门数"""
        from app.models.score import Score

        query = self.db.query(Score).filter(
            Score.student_id == student_id,
            Score.score < 60  # 不及格
        )

        if start_date:
            query = query.filter(Score.created_at >= start_date)

        return query.count()

    def _calc_gpa(self, student_id: int, start_date: Optional[datetime],
                  extra: Dict[str, Any]) -> float:
        """
        计算GPA（平均绩点）

        采用标准4.0制:
        - 90-100: 4.0
        - 85-89: 3.7
        - 82-84: 3.3
        - 78-81: 3.0
        - 75-77: 2.7
        - 72-74: 2.3
        - 68-71: 2.0
        - 64-67: 1.5
        - 60-63: 1.0
        - <60: 0
        """
        from app.models.score import Score
        from app.models.course import Course

        query = self.db.query(Score).join(Course).filter(
            Score.student_id == student_id
        )

        if start_date:
            query = query.filter(Score.created_at >= start_date)

        scores = query.all()

        if not scores:
            return 0.0

        total_credits = 0
        total_gpa_points = 0.0

        for score in scores:
            if score.score is None:
                continue

            course = score.course
            credits = course.credit if course else 1

            # 计算绩点
            grade_point = self._score_to_gpa(float(score.score))

            total_credits += credits
            total_gpa_points += grade_point * credits

        return round(total_gpa_points / total_credits, 2) if total_credits > 0 else 0.0

    def _score_to_gpa(self, score: float) -> float:
        """将百分制成绩转换为绩点"""
        if score >= 90:
            return 4.0
        elif score >= 85:
            return 3.7
        elif score >= 82:
            return 3.3
        elif score >= 78:
            return 3.0
        elif score >= 75:
            return 2.7
        elif score >= 72:
            return 2.3
        elif score >= 68:
            return 2.0
        elif score >= 64:
            return 1.5
        elif score >= 60:
            return 1.0
        else:
            return 0.0

    def _calc_absence_rate(self, student_id: int, start_date: Optional[datetime],
                           extra: Dict[str, Any]) -> float:
        """计算缺勤率"""
        from app.models.attendance import Attendance, AttendanceStatus

        query = self.db.query(Attendance).filter(
            Attendance.student_id == student_id
        )

        if start_date:
            query = query.filter(Attendance.date >= start_date.date())

        attendances = query.all()

        if not attendances:
            return 0.0

        # 统计缺勤次数（包括旷课和请假）
        absent_count = sum(
            1 for a in attendances
            if a.status in [AttendanceStatus.ABSENT, AttendanceStatus.LEAVE]
        )

        return round(absent_count / len(attendances), 4)

    def _calc_absence_count(self, student_id: int, start_date: Optional[datetime],
                            extra: Dict[str, Any]) -> int:
        """计算缺勤次数"""
        from app.models.attendance import Attendance, AttendanceStatus

        query = self.db.query(Attendance).filter(
            Attendance.student_id == student_id,
            Attendance.status == AttendanceStatus.ABSENT
        )

        if start_date:
            query = query.filter(Attendance.date >= start_date.date())

        return query.count()

    def _calc_credit_ratio(self, student_id: int, start_date: Optional[datetime],
                           extra: Dict[str, Any]) -> float:
        """计算学分完成率"""
        from app.models.score import Score
        from app.models.course import Course
        from app.models.student import Student

        # 获取学生班级信息
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student or not student.class_info:
            return 0.0

        # 获取已通过课程的总学分
        passed_query = self.db.query(Score).join(Course).filter(
            Score.student_id == student_id,
            Score.score >= 60
        )
        passed_scores = passed_query.all()

        passed_credits = sum(
            s.course.credit for s in passed_scores
            if s.course and s.course.credit
        )

        # 获取该班级应修总学分（这里简化处理，实际应根据培养方案计算）
        # 假设每学期约20学分
        expected_credits = 20 * max(1, student.grade % 100 - student.class_info.grade % 100 + 1)

        return round(passed_credits / expected_credits, 2) if expected_credits > 0 else 0.0

    def _calc_continuous_absence(self, student_id: int, start_date: Optional[datetime],
                                 extra: Dict[str, Any]) -> int:
        """计算连续缺勤天数"""
        from app.models.attendance import Attendance, AttendanceStatus

        query = self.db.query(Attendance).filter(
            Attendance.student_id == student_id
        )

        if start_date:
            query = query.filter(Attendance.date >= start_date.date())

        query = query.order_by(Attendance.date.asc())
        attendances = query.all()

        if not attendances:
            return 0

        # 计算最长连续缺勤
        max_continuous = 0
        current_continuous = 0

        for a in attendances:
            if a.status == AttendanceStatus.ABSENT:
                current_continuous += 1
                max_continuous = max(max_continuous, current_continuous)
            else:
                current_continuous = 0

        return max_continuous


class RuleExecutor:
    """规则执行器"""

    def __init__(self, db: Session):
        self.db = db
        self.parser = RuleParser()
        self.calculator = MetricCalculator(db)

    def execute(self, student_id: int, conditions: Dict[str, Any]) -> ExecutionResult:
        """
        执行单条规则

        Args:
            student_id: 学生ID
            conditions: 规则条件JSON

        Returns:
            执行结果
        """
        # 解析规则
        parsed = self.parser.parse(conditions)

        # 计算指标值
        metric_value = self.calculator.calculate(
            student_id=student_id,
            metric=parsed.metric,
            time_window=parsed.time_window,
            extra=parsed.extra
        )

        # 如果无法计算指标值，不触发预警
        if metric_value is None:
            return ExecutionResult(
                triggered=False,
                metric_value=None,
                threshold=parsed.threshold,
                details={"reason": "无法计算指标值"}
            )

        # 执行比较
        triggered = compare(parsed.operator, metric_value, parsed.threshold)

        return ExecutionResult(
            triggered=triggered,
            metric_value=metric_value,
            threshold=parsed.threshold,
            details={
                "metric": parsed.metric,
                "operator": parsed.operator,
                "actual_value": metric_value,
                "expected_threshold": parsed.threshold
            }
        )

    def execute_with_aggregation(self, student_id: int,
                                  conditions: Dict[str, Any]) -> ExecutionResult:
        """
        执行带有聚合函数的规则

        用于处理多条数据需要聚合后比较的场景
        例如：多门课程平均分低于60
        """
        from app.models.score import Score

        parsed = self.parser.parse(conditions)

        # 获取相关数据
        data_list = self._get_data_for_metric(student_id, parsed)

        if not data_list:
            return ExecutionResult(
                triggered=False,
                metric_value=None,
                threshold=parsed.threshold,
                details={"reason": "无相关数据"}
            )

        # 应用聚合函数
        if parsed.aggregation:
            metric_value = aggregate(parsed.aggregation, data_list)
        else:
            metric_value = data_list[0] if data_list else None

        # 检查最小数量要求
        if parsed.min_count and len(data_list) < parsed.min_count:
            return ExecutionResult(
                triggered=False,
                metric_value=metric_value,
                threshold=parsed.threshold,
                details={
                    "reason": f"数据数量不足，需要至少{parsed.min_count}条，实际{len(data_list)}条"
                }
            )

        # 执行比较
        triggered = compare(parsed.operator, metric_value, parsed.threshold)

        return ExecutionResult(
            triggered=triggered,
            metric_value=metric_value,
            threshold=parsed.threshold,
            details={
                "aggregation": parsed.aggregation,
                "data_count": len(data_list),
                "actual_value": metric_value,
                "expected_threshold": parsed.threshold
            }
        )

    def _get_data_for_metric(self, student_id: int,
                             parsed: ParsedRule) -> List[Any]:
        """根据指标类型获取数据列表"""
        from app.models.score import Score
        from app.models.attendance import Attendance, AttendanceStatus

        start_date = self.calculator._parse_time_window(parsed.time_window)

        data_list = []

        if parsed.metric == "score":
            # 获取成绩列表
            query = self.db.query(Score.score).filter(
                Score.student_id == student_id,
                Score.score.isnot(None)
            )
            if start_date:
                query = query.filter(Score.created_at >= start_date)

            # 课程过滤
            if parsed.extra and "course_id" in parsed.extra:
                query = query.filter(Score.course_id == parsed.extra["course_id"])

            data_list = [float(r[0]) for r in query.all()]

        elif parsed.metric == "absence_rate":
            # 获取缺勤状态列表
            query = self.db.query(Attendance.status).filter(
                Attendance.student_id == student_id
            )
            if start_date:
                query = query.filter(Attendance.date >= start_date.date())

            # 转换为布尔值（缺勤为True）
            data_list = [
                r[0] in [AttendanceStatus.ABSENT, AttendanceStatus.LEAVE]
                for r in query.all()
            ]

        elif parsed.metric == "fail_count":
            # 获取不及格成绩
            query = self.db.query(Score.score).filter(
                Score.student_id == student_id,
                Score.score < 60
            )
            if start_date:
                query = query.filter(Score.created_at >= start_date)

            data_list = [float(r[0]) for r in query.all()]

        return data_list

    def batch_execute(self, student_ids: List[int],
                      conditions: Dict[str, Any]) -> Dict[int, ExecutionResult]:
        """
        批量执行规则

        Args:
            student_ids: 学生ID列表
            conditions: 规则条件

        Returns:
            学生ID -> 执行结果的映射
        """
        results = {}
        for student_id in student_ids:
            results[student_id] = self.execute(student_id, conditions)
        return results
