"""
规则引擎 - 主引擎类

整合解析器和执行器，提供完整的规则处理能力
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json

from sqlalchemy.orm import Session

from app.core.rule_engine.parser import RuleParser, ParsedRule
from app.core.rule_engine.executor import RuleExecutor, ExecutionResult
from app.models.rule import Rule, RuleType, AlertLevel, COMPREHENSIVE_RULE_CODE
from app.models.alert import Alert, AlertStatus
from app.models.student import Student


@dataclass
class AlertCandidate:
    """预警候选对象"""
    student_id: int
    rule_id: int
    level: AlertLevel
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class RuleEngine:
    """
    规则引擎主类

    职责：
    1. 加载和管理规则
    2. 对学生执行规则检测
    3. 生成预警信息
    4. 提供规则验证和描述转换功能
    """

    def __init__(self, db: Session):
        self.db = db
        self.parser = RuleParser()
        self.executor = RuleExecutor(db)

    # ========== 规则管理 ==========

    def load_rule(self, rule_id: int) -> Optional[Rule]:
        """加载单条规则"""
        return self.db.query(Rule).filter(Rule.id == rule_id).first()

    def load_active_rules(self, rule_type: Optional[RuleType] = None) -> List[Rule]:
        """
        加载所有启用的规则

        Args:
            rule_type: 可选，按类型过滤

        Returns:
            启用的规则列表
        """
        query = self.db.query(Rule).filter(Rule.is_active == True)

        if rule_type:
            query = query.filter(Rule.type == rule_type)

        return query.all()

    def validate_rule(self, conditions: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证规则条件格式

        Args:
            conditions: 规则条件JSON

        Returns:
            (是否有效, 错误信息)
        """
        try:
            self.parser.validate(conditions)
            return True, ""
        except ValueError as e:
            return False, str(e)

    def describe_rule(self, conditions: Dict[str, Any]) -> str:
        """
        将规则条件转换为可读描述

        Args:
            conditions: 规则条件JSON

        Returns:
            可读描述字符串
        """
        return self.parser.to_description(conditions)

    # ========== 规则执行 ==========

    def execute_rule(self, rule: Rule, student_id: int) -> ExecutionResult:
        """
        对单个学生执行单条规则

        Args:
            rule: 规则对象
            student_id: 学生ID

        Returns:
            执行结果
        """
        conditions = rule.conditions

        # 检查是否需要聚合
        if conditions.get("aggregation"):
            return self.executor.execute_with_aggregation(student_id, conditions)
        else:
            return self.executor.execute(student_id, conditions)

    def execute_rule_for_students(self, rule: Rule,
                                   student_ids: List[int]) -> Dict[int, ExecutionResult]:
        """
        对多个学生执行单条规则

        Args:
            rule: 规则对象
            student_ids: 学生ID列表

        Returns:
            学生ID -> 执行结果的映射
        """
        results = {}
        for student_id in student_ids:
            results[student_id] = self.execute_rule(rule, student_id)
        return results

    def execute_all_rules(self, student_id: int,
                          rule_types: Optional[List[RuleType]] = None) -> Dict[int, ExecutionResult]:
        """
        对单个学生执行所有启用的规则

        Args:
            student_id: 学生ID
            rule_types: 可选，限制规则类型

        Returns:
            规则ID -> 执行结果的映射
        """
        results = {}

        # 加载规则
        if rule_types:
            rules = []
            for rt in rule_types:
                rules.extend(self.load_active_rules(rt))
        else:
            rules = self.load_active_rules()

        for rule in rules:
            results[rule.id] = self.execute_rule(rule, student_id)

        return results

    # ========== 预警生成 ==========

    def generate_alerts(self, rule: Rule,
                        student_ids: Optional[List[int]] = None) -> List[AlertCandidate]:
        """
        根据规则生成预警候选列表

        Args:
            rule: 规则对象
            student_ids: 可选，指定学生ID列表；为空则检测所有学生

        Returns:
            预警候选对象列表
        """
        candidates = []

        # 获取学生列表
        if student_ids is None:
            students = self.db.query(Student).filter(Student.is_active == True).all()
            student_ids = [s.id for s in students]

        # 执行规则
        results = self.execute_rule_for_students(rule, student_ids)

        # 筛选触发的预警
        for student_id, result in results.items():
            if result.triggered:
                student = self.db.query(Student).filter(Student.id == student_id).first()
                if student:
                    message = self._generate_alert_message(rule, student, result)
                    candidates.append(AlertCandidate(
                        student_id=student_id,
                        rule_id=rule.id,
                        level=rule.level,
                        message=message,
                        details=result.details
                    ))

        return candidates

    def _generate_alert_message(self, rule: Rule, student: Student,
                                result: ExecutionResult) -> str:
        """
        生成预警消息

        Args:
            rule: 规则对象
            student: 学生对象
            result: 执行结果

        Returns:
            预警消息字符串
        """
        # 基础消息模板
        templates = {
            RuleType.SCORE: f"学生{student.name}({student.student_no})成绩预警：{rule.description or rule.name}",
            RuleType.ATTENDANCE: f"学生{student.name}({student.student_no})考勤预警：{rule.description or rule.name}",
        }

        if rule.code == COMPREHENSIVE_RULE_CODE:
            base_message = f"学生{student.name}({student.student_no})综合预警：{rule.description or rule.name}"
        else:
            base_message = templates.get(rule.type, f"学生{student.name}预警：{rule.name}")

        # 添加详细信息
        if result.details:
            detail_parts = []
            if "actual_value" in result.details:
                detail_parts.append(f"实际值: {result.details['actual_value']}")
            if "expected_threshold" in result.details:
                detail_parts.append(f"阈值: {result.details['expected_threshold']}")

            if detail_parts:
                base_message += f"（{', '.join(detail_parts)}）"

        return base_message

    def create_alerts_from_candidates(self, candidates: List[AlertCandidate]) -> List[Alert]:
        """
        将预警候选转换为实际的预警记录

        Args:
            candidates: 预警候选列表

        Returns:
            创建的预警记录列表
        """
        alerts = []

        for candidate in candidates:
            # 检查是否已存在相同的学生-规则-未处理预警
            existing = self.db.query(Alert).filter(
                Alert.student_id == candidate.student_id,
                Alert.rule_id == candidate.rule_id,
                Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING])
            ).first()

            if existing:
                continue  # 跳过已存在的预警

            # 创建新预警
            alert = Alert(
                student_id=candidate.student_id,
                rule_id=candidate.rule_id,
                level=candidate.level,
                message=candidate.message,
                status=AlertStatus.PENDING
            )
            self.db.add(alert)
            alerts.append(alert)

        if alerts:
            self.db.commit()

        return alerts

    # ========== 高级接口 ==========

    def run_detection(self, rule_id: Optional[int] = None,
                      student_ids: Optional[List[int]] = None,
                      rule_type: Optional[RuleType] = None) -> Dict[str, Any]:
        """
        运行预警检测（高级接口）

        Args:
            rule_id: 可选，指定规则ID；为空则使用所有启用的规则
            student_ids: 可选，指定学生ID列表；为空则检测所有学生
            rule_type: 可选，指定规则类型

        Returns:
            检测结果统计
        """
        stats = {
            "total_checked": 0,
            "total_triggered": 0,
            "alerts_created": 0,
            "rules_executed": 0,
            "details": []
        }

        # 确定要执行的规则
        if rule_id:
            rules = [self.load_rule(rule_id)]
            rules = [r for r in rules if r]  # 过滤None
        else:
            rules = self.load_active_rules(rule_type)

        if not rules:
            return stats

        # 确定学生范围
        if student_ids is None:
            students = self.db.query(Student).filter(Student.is_active == True).all()
            student_ids = [s.id for s in students]

        stats["total_checked"] = len(student_ids)
        stats["rules_executed"] = len(rules)

        # 执行每条规则
        all_candidates = []
        for rule in rules:
            candidates = self.generate_alerts(rule, student_ids)
            all_candidates.extend(candidates)

            stats["details"].append({
                "rule_id": rule.id,
                "rule_name": rule.name,
                "triggered_count": len(candidates)
            })

        stats["total_triggered"] = len(all_candidates)

        # 创建预警记录
        alerts = self.create_alerts_from_candidates(all_candidates)
        stats["alerts_created"] = len(alerts)

        return stats

    def get_student_risk_assessment(self, student_id: int) -> Dict[str, Any]:
        """
        获取学生风险评估报告

        Args:
            student_id: 学生ID

        Returns:
            风险评估报告
        """
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {"error": "学生不存在"}

        # 执行所有规则
        results = self.execute_all_rules(student_id)

        # 统计分析
        triggered_rules = []
        risk_score = 0

        level_weights = {
            AlertLevel.WARNING: 1,
            AlertLevel.SERIOUS: 2,
            AlertLevel.URGENT: 3
        }

        for rule_id, result in results.items():
            if result.triggered:
                rule = self.load_rule(rule_id)
                if rule:
                    triggered_rules.append({
                        "rule_id": rule_id,
                        "rule_name": rule.name,
                        "rule_type": rule.type.value,
                        "level": rule.level.value,
                        "details": result.details
                    })
                    risk_score += level_weights.get(rule.level, 1)

        # 风险等级判定
        if risk_score >= 5:
            risk_level = "high"
        elif risk_score >= 2:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "student_id": student_id,
            "student_name": student.name,
            "student_no": student.student_no,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "triggered_rules": triggered_rules,
            "total_rules_checked": len(results),
            "triggered_count": len(triggered_rules),
            "assessment_time": datetime.now().isoformat()
        }

    # ========== 规则测试接口 ==========

    def test_rule(self, conditions: Dict[str, Any],
                  test_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        测试规则（用于规则配置时的验证）

        Args:
            conditions: 规则条件
            test_data: 可选的测试数据

        Returns:
            测试结果
        """
        result = {
            "valid": False,
            "description": "",
            "error": None,
            "sample_result": None
        }

        try:
            # 验证规则格式
            valid, error = self.validate_rule(conditions)
            if not valid:
                result["error"] = error
                return result

            result["valid"] = True
            result["description"] = self.describe_rule(conditions)

            # 如果提供了测试数据，执行测试
            if test_data and "student_id" in test_data:
                exec_result = self.executor.execute(test_data["student_id"], conditions)
                result["sample_result"] = {
                    "triggered": exec_result.triggered,
                    "metric_value": exec_result.metric_value,
                    "threshold": exec_result.threshold,
                    "details": exec_result.details
                }

        except Exception as e:
            result["error"] = str(e)

        return result


# ========== 工厂函数 ==========

def create_rule_engine(db: Session) -> RuleEngine:
    """
    创建规则引擎实例

    Args:
        db: 数据库会话

    Returns:
        规则引擎实例
    """
    return RuleEngine(db)
