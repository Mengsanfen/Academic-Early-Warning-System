"""
规则引擎 - 规则解析器
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum


class MetricType(str, Enum):
    """指标类型"""
    SCORE = "score"                    # 成绩
    FAIL_COUNT = "fail_count"          # 挂科数
    GPA = "gpa"                        # 平均绩点
    ABSENCE_RATE = "absence_rate"      # 缺勤率
    ABSENCE_COUNT = "absence_count"    # 缺勤次数
    CREDIT_RATIO = "credit_ratio"      # 学分完成率
    CONTINUOUS_ABSENCE = "continuous_absence"  # 连续缺勤


@dataclass
class ParsedRule:
    """解析后的规则对象"""
    metric: str                # 指标名称
    operator: str              # 比较操作符
    threshold: Any             # 阈值
    aggregation: Optional[str] = None  # 聚合函数
    time_window: Optional[str] = None  # 时间窗口
    min_count: Optional[int] = None    # 最小数量
    extra: Dict[str, Any] = None       # 额外参数


class RuleParser:
    """规则解析器"""

    # 必需字段
    REQUIRED_FIELDS = ["metric", "operator", "threshold"]

    # 可选字段
    OPTIONAL_FIELDS = ["aggregation", "time_window", "min_count"]

    def parse(self, conditions: Dict[str, Any]) -> ParsedRule:
        """
        解析规则条件

        Args:
            conditions: JSON格式的规则条件

        Returns:
            解析后的规则对象

        Raises:
            ValueError: 规则格式无效
        """
        # 验证必需字段
        self.validate(conditions)

        # 提取字段
        metric = conditions["metric"]
        operator = conditions["operator"]
        threshold = conditions["threshold"]
        aggregation = conditions.get("aggregation")
        time_window = conditions.get("time_window")
        min_count = conditions.get("min_count")

        # 收集额外参数
        extra = {}
        for key, value in conditions.items():
            if key not in self.REQUIRED_FIELDS and key not in self.OPTIONAL_FIELDS:
                extra[key] = value

        return ParsedRule(
            metric=metric,
            operator=operator,
            threshold=threshold,
            aggregation=aggregation,
            time_window=time_window,
            min_count=min_count,
            extra=extra if extra else None
        )

    def validate(self, conditions: Dict[str, Any]) -> bool:
        """
        验证规则条件格式

        Args:
            conditions: JSON格式的规则条件

        Returns:
            是否有效

        Raises:
            ValueError: 规则格式无效
        """
        if not isinstance(conditions, dict):
            raise ValueError("规则条件必须是字典格式")

        # 检查必需字段
        for field in self.REQUIRED_FIELDS:
            if field not in conditions:
                raise ValueError(f"缺少必需字段: {field}")

        # 验证操作符
        from app.core.rule_engine.operators import OPERATORS
        if conditions["operator"] not in OPERATORS:
            raise ValueError(f"无效的操作符: {conditions['operator']}")

        # 验证聚合函数（如果有）
        if "aggregation" in conditions:
            from app.core.rule_engine.aggregators import AGGREGATORS
            if conditions["aggregation"] not in AGGREGATORS:
                raise ValueError(f"无效的聚合函数: {conditions['aggregation']}")

        return True

    def to_description(self, conditions: Dict[str, Any]) -> str:
        """
        将规则条件转换为可读描述

        Args:
            conditions: JSON格式的规则条件

        Returns:
            可读描述
        """
        parsed = self.parse(conditions)

        # 指标名称映射
        metric_names = {
            "score": "成绩",
            "fail_count": "挂科门数",
            "gpa": "GPA",
            "absence_rate": "缺勤率",
            "absence_count": "缺勤次数",
            "credit_ratio": "学分完成率",
            "continuous_absence": "连续缺勤"
        }

        # 操作符映射
        operator_names = {
            "==": "等于",
            "!=": "不等于",
            ">": "大于",
            ">=": "大于等于",
            "<": "小于",
            "<=": "小于等于"
        }

        metric_name = metric_names.get(parsed.metric, parsed.metric)
        operator_name = operator_names.get(parsed.operator, parsed.operator)

        desc = f"{metric_name} {operator_name} {parsed.threshold}"

        if parsed.min_count:
            desc = f"{metric_name}满足条件数 >= {parsed.min_count}"

        return desc
