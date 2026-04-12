"""
轻量级规则引擎 - 简化版

基于 Python operator 模块实现安全的动态规则解析
包含完善的错误处理和容错机制
"""
import operator
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.rule_engine.comprehensive_rule import ensure_comprehensive_rule, evaluate_comprehensive_rule
from app.models.rule import COMPREHENSIVE_RULE_CODE, COMPREHENSIVE_RULE_MODE

logger = logging.getLogger(__name__)


class RuleEngineError(Exception):
    """规则引擎自定义异常"""
    pass


class SimpleRuleEngine:
    """
    轻量级规则引擎

    功能：
    1. 解析 JSON 格式的规则条件
    2. 安全执行比较运算
    3. 计算学生各项指标
    4. 生成预警记录
    """

    # 支持的比较运算符映射
    OPERATORS = {
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        '==': operator.eq,
        '!=': operator.ne,
        'lt': operator.lt,
        'le': operator.le,
        'gt': operator.gt,
        'ge': operator.ge,
        'eq': operator.eq,
        'ne': operator.ne,
    }

    # 指标类型定义
    METRIC_TYPES = {
        'score',           # 单科成绩
        'avg_score',       # 平均成绩
        'fail_count',      # 挂科门数
        'gpa',             # 绩点
        'attendance_rate', # 出勤率
        'absence_count',   # 缺勤次数
        'late_count',      # 迟到次数
    }

    def __init__(self, db: Session):
        self.db = db

    # ==================== 核心执行接口 ====================

    def execute_all_rules(self) -> Dict[str, Any]:
        """
        执行所有启用的规则，对全部学生进行检测

        Returns:
            执行结果统计
        """
        from app.models.rule import Rule, RuleType
        from app.models.student import Student
        from app.models.alert import Alert, AlertStatus

        stats = {
            "total_students": 0,
            "total_rules": 0,
            "total_checked": 0,
            "total_triggered": 0,
            "alerts_created": 0,
            "errors": [],
            "rule_details": []
        }

        try:
            # 1. 加载所有启用的规则
            ensure_comprehensive_rule(self.db)
            rules = self.db.query(Rule).filter(Rule.is_active == True).all()
            if not rules:
                logger.warning("没有找到启用的规则")
                return stats

            stats["total_rules"] = len(rules)

            # 2. 加载所有活跃学生
            students = self.db.query(Student).filter(Student.is_active == True).all()
            if not students:
                logger.warning("没有找到活跃的学生")
                return stats

            stats["total_students"] = len(students)
            stats["total_checked"] = len(students)

            # 3. 逐条规则执行
            for rule in rules:
                rule_result = self._execute_single_rule(rule, students, stats)
                stats["rule_details"].append(rule_result)

            self.db.commit()
            logger.info(f"规则执行完成: 检查 {stats['total_checked']} 名学生, "
                       f"触发 {stats['total_triggered']} 次, "
                       f"创建 {stats['alerts_created']} 条预警")

        except Exception as e:
            self.db.rollback()
            error_msg = f"规则引擎执行失败: {str(e)}"
            logger.exception(error_msg)
            stats["errors"].append(error_msg)

        return stats

    def _execute_single_rule(self, rule: Any, students: List[Any],
                            stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单条规则

        Args:
            rule: 规则对象
            students: 学生列表
            stats: 统计信息字典

        Returns:
            规则执行结果
        """
        from app.models.alert import Alert, AlertStatus

        result = {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "rule_code": rule.code,
            "triggered_count": 0,
            "alerts_created": 0,
            "error": None
        }

        try:
            # 解析规则条件
            conditions = self._parse_conditions(rule.conditions)
            if conditions is None:
                result["error"] = "规则条件解析失败"
                return result

            if (
                rule.code == COMPREHENSIVE_RULE_CODE
                or conditions.get("mode") == COMPREHENSIVE_RULE_MODE
            ):
                for student in students:
                    try:
                        evaluation = evaluate_comprehensive_rule(student.id, self.db, rule)
                        if evaluation.get("triggered"):
                            stats["total_triggered"] += 1
                            result["triggered_count"] += 1
                        if evaluation.get("alert_created"):
                            stats["alerts_created"] += 1
                            result["alerts_created"] += 1
                    except Exception as e:
                        logger.warning(f"澶勭悊瀛︾敓 {student.id} 缁煎悎瑙勫垯 {rule.id} 鏃跺嚭閿? {e}")
                        continue
                return result

            metric_type = conditions.get("metric")
            threshold = conditions.get("threshold")
            op_str = conditions.get("operator", "<")
            time_window = conditions.get("time_window")

            # 验证必要字段
            if metric_type is None or threshold is None:
                result["error"] = f"规则条件缺少必要字段: metric={metric_type}, threshold={threshold}"
                return result

            # 获取比较运算符
            op_func = self.OPERATORS.get(op_str)
            if op_func is None:
                result["error"] = f"不支持的比较运算符: {op_str}"
                return result

            # 遍历学生进行检测
            for student in students:
                try:
                    # 计算指标值
                    metric_value = self._calculate_metric(
                        student.id, metric_type, time_window
                    )

                    # 如果无法计算（如无数据），跳过该学生
                    if metric_value is None:
                        continue

                    # 执行比较
                    if op_func(metric_value, threshold):
                        stats["total_triggered"] += 1
                        result["triggered_count"] += 1

                        # 检查是否已存在未处理的重复预警
                        existing = self.db.query(Alert).filter(
                            Alert.student_id == student.id,
                            Alert.rule_id == rule.id,
                            Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING])
                        ).first()

                        if existing:
                            logger.debug(f"学生 {student.id} 已存在未处理的规则 {rule.id} 预警，跳过")
                            continue

                        # 创建新预警
                        message = self._generate_message(rule, student, metric_value, threshold)
                        alert = Alert(
                            student_id=student.id,
                            rule_id=rule.id,
                            level=rule.level,
                            message=message,
                            status=AlertStatus.PENDING
                        )
                        self.db.add(alert)
                        stats["alerts_created"] += 1
                        result["alerts_created"] += 1

                except Exception as e:
                    logger.warning(f"处理学生 {student.id} 规则 {rule.id} 时出错: {e}")
                    continue

        except Exception as e:
            error_msg = f"执行规则 {rule.id} 失败: {str(e)}"
            logger.exception(error_msg)
            result["error"] = error_msg
            stats["errors"].append(error_msg)

        return result

    # ==================== 条件解析 ====================

    def _parse_conditions(self, conditions: Any) -> Optional[Dict[str, Any]]:
        """
        安全解析规则条件

        Args:
            conditions: 规则条件（可能是 dict 或 JSON 字符串）

        Returns:
            解析后的条件字典，失败返回 None
        """
        import json

        if conditions is None:
            return None

        try:
            # 如果已经是字典，直接返回
            if isinstance(conditions, dict):
                return conditions

            # 如果是字符串，尝试解析 JSON
            if isinstance(conditions, str):
                return json.loads(conditions)

            logger.warning(f"未知的条件类型: {type(conditions)}")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解析条件时出错: {e}")
            return None

    # ==================== 指标计算 ====================

    def _calculate_metric(self, student_id: int, metric_type: str,
                         time_window: Optional[str] = None) -> Optional[float]:
        """
        计算学生指标值

        Args:
            student_id: 学生ID
            metric_type: 指标类型
            time_window: 时间窗口

        Returns:
            指标值，无法计算时返回 None
        """
        try:
            # 解析时间窗口
            start_date = self._parse_time_window(time_window)

            # 根据指标类型调用对应计算方法
            if metric_type == "score":
                return self._calc_latest_score(student_id, start_date)
            elif metric_type == "avg_score":
                return self._calc_avg_score(student_id, start_date)
            elif metric_type == "fail_count":
                return self._calc_fail_count(student_id, start_date)
            elif metric_type == "gpa":
                return self._calc_gpa(student_id, start_date)
            elif metric_type == "attendance_rate":
                return self._calc_attendance_rate(student_id, start_date)
            elif metric_type == "absence_count":
                return self._calc_absence_count(student_id, start_date)
            elif metric_type == "late_count":
                return self._calc_late_count(student_id, start_date)
            else:
                logger.warning(f"未知的指标类型: {metric_type}")
                return None

        except Exception as e:
            logger.error(f"计算学生 {student_id} 指标 {metric_type} 时出错: {e}")
            return None

    def _parse_time_window(self, time_window: Optional[str]) -> Optional[datetime]:
        """解析时间窗口"""
        if not time_window:
            return None

        now = datetime.now()
        window_map = {
            "1周": timedelta(weeks=1),
            "2周": timedelta(weeks=2),
            "1个月": timedelta(days=30),
            "3个月": timedelta(days=90),
            "1学期": timedelta(days=150),
            "1学年": timedelta(days=365),
            "本学期": timedelta(days=150),
        }

        delta = window_map.get(time_window)
        if delta:
            return now - delta
        return None

    def _calc_latest_score(self, student_id: int,
                          start_date: Optional[datetime]) -> Optional[float]:
        """计算最新一门成绩"""
        from app.models.score import Score

        try:
            query = self.db.query(Score).filter(Score.student_id == student_id)
            if start_date:
                query = query.filter(Score.created_at >= start_date)

            score = query.order_by(Score.created_at.desc()).first()
            if score and score.score is not None:
                return float(score.score)
            return None
        except Exception as e:
            logger.error(f"查询最新成绩失败: {e}")
            return None

    def _calc_avg_score(self, student_id: int,
                       start_date: Optional[datetime]) -> Optional[float]:
        """计算平均成绩"""
        from app.models.score import Score

        try:
            query = self.db.query(Score).filter(
                Score.student_id == student_id,
                Score.score.isnot(None)
            )
            if start_date:
                query = query.filter(Score.created_at >= start_date)

            scores = query.all()
            if not scores:
                return None

            total = sum(float(s.score) for s in scores)
            return round(total / len(scores), 2)
        except Exception as e:
            logger.error(f"计算平均成绩失败: {e}")
            return None

    def _calc_fail_count(self, student_id: int,
                        start_date: Optional[datetime]) -> int:
        """计算挂科门数"""
        from app.models.score import Score

        try:
            query = self.db.query(Score).filter(
                Score.student_id == student_id,
                Score.score < 60
            )
            if start_date:
                query = query.filter(Score.created_at >= start_date)

            return query.count()
        except Exception as e:
            logger.error(f"计算挂科门数失败: {e}")
            return 0

    def _calc_gpa(self, student_id: int,
                  start_date: Optional[datetime]) -> float:
        """计算 GPA（标准4.0制）"""
        from app.models.score import Score
        from app.models.course import Course

        try:
            query = self.db.query(Score).join(
                Course, Score.course_id == Course.id
            ).filter(Score.student_id == student_id)

            if start_date:
                query = query.filter(Score.created_at >= start_date)

            scores = query.all()
            if not scores:
                return 0.0

            total_credits = 0.0
            total_points = 0.0

            for score in scores:
                if score.score is None:
                    continue

                credit = float(score.course.credit) if score.course and score.course.credit else 1.0
                gpa_point = self._score_to_gpa(float(score.score))

                total_credits += credit
                total_points += gpa_point * credit

            if total_credits == 0:
                return 0.0

            return round(total_points / total_credits, 2)
        except Exception as e:
            logger.error(f"计算GPA失败: {e}")
            return 0.0

    def _score_to_gpa(self, score: float) -> float:
        """百分制转绩点"""
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

    def _calc_attendance_rate(self, student_id: int,
                              start_date: Optional[datetime]) -> float:
        """计算出勤率（正常出勤的比例）"""
        from app.models.attendance import Attendance, AttendanceStatus

        try:
            query = self.db.query(Attendance).filter(
                Attendance.student_id == student_id
            )
            if start_date:
                query = query.filter(Attendance.date >= start_date.date())

            attendances = query.all()
            if not attendances:
                return 1.0  # 无考勤记录默认全勤

            present_count = sum(
                1 for a in attendances
                if a.status == AttendanceStatus.PRESENT
            )

            return round(present_count / len(attendances), 4)
        except Exception as e:
            logger.error(f"计算出勤率失败: {e}")
            return 1.0

    def _calc_absence_count(self, student_id: int,
                           start_date: Optional[datetime]) -> int:
        """计算缺勤次数"""
        from app.models.attendance import Attendance, AttendanceStatus

        try:
            query = self.db.query(Attendance).filter(
                Attendance.student_id == student_id,
                Attendance.status == AttendanceStatus.ABSENT
            )
            if start_date:
                query = query.filter(Attendance.date >= start_date.date())

            return query.count()
        except Exception as e:
            logger.error(f"计算缺勤次数失败: {e}")
            return 0

    def _calc_late_count(self, student_id: int,
                        start_date: Optional[datetime]) -> int:
        """计算迟到次数"""
        from app.models.attendance import Attendance, AttendanceStatus

        try:
            query = self.db.query(Attendance).filter(
                Attendance.student_id == student_id,
                Attendance.status == AttendanceStatus.LATE
            )
            if start_date:
                query = query.filter(Attendance.date >= start_date.date())

            return query.count()
        except Exception as e:
            logger.error(f"计算迟到次数失败: {e}")
            return 0

    # ==================== 消息生成 ====================

    def _generate_message(self, rule: Any, student: Any,
                         metric_value: float, threshold: float) -> str:
        """生成预警消息"""
        try:
            # 使用模板或生成默认消息
            if rule.message_template:
                message = rule.message_template.format(
                    student_name=student.name,
                    student_no=student.student_no,
                    metric_value=metric_value,
                    threshold=threshold,
                    rule_name=rule.name
                )
            else:
                message = f"学生{student.name}({student.student_no})触发预警：{rule.name}，" \
                         f"当前值{metric_value}，阈值{threshold}"

            return message
        except Exception as e:
            logger.warning(f"生成消息失败: {e}")
            return f"学生{student.name}({student.student_no})触发预警：{rule.name}"


# ==================== 便捷函数 ====================

def run_rule_detection(db: Session) -> Dict[str, Any]:
    """
    运行规则检测的便捷函数

    Args:
        db: 数据库会话

    Returns:
        检测结果
    """
    engine = SimpleRuleEngine(db)
    return engine.execute_all_rules()
