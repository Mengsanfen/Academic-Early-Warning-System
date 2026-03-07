"""
规则引擎模块

基于多源数据的学业预警系统核心组件
采用可配置的JSON规则格式，支持灵活的指标计算和预警触发

主要组件：
- SimpleRuleEngine: 轻量级规则引擎（推荐使用）
- RuleEngine: 完整版规则引擎（保留向后兼容）

使用示例:
    from app.core.rule_engine import SimpleRuleEngine, run_rule_detection

    # 使用便捷函数直接运行检测
    result = run_rule_detection(db)

    # 或创建引擎实例
    engine = SimpleRuleEngine(db)
    result = engine.execute_all_rules()
"""

# 新版轻量级引擎（推荐）
from app.core.rule_engine.simple_engine import (
    SimpleRuleEngine,
    RuleEngineError,
    run_rule_detection
)

# 保留旧版引擎用于向后兼容
from app.core.rule_engine.parser import RuleParser, ParsedRule, MetricType
from app.core.rule_engine.operators import OPERATORS, get_operator, compare
from app.core.rule_engine.aggregators import AGGREGATORS, get_aggregator, aggregate
from app.core.rule_engine.executor import (
    RuleExecutor,
    MetricCalculator,
    ExecutionResult
)
from app.core.rule_engine.engine import (
    RuleEngine,
    AlertCandidate,
    create_rule_engine
)


__all__ = [
    # 新版轻量级引擎（推荐使用）
    "SimpleRuleEngine",
    "RuleEngineError",
    "run_rule_detection",

    # 旧版主引擎（向后兼容）
    "RuleEngine",
    "create_rule_engine",

    # 解析器
    "RuleParser",
    "ParsedRule",
    "MetricType",

    # 执行器
    "RuleExecutor",
    "MetricCalculator",
    "ExecutionResult",

    # 预警候选
    "AlertCandidate",

    # 操作符
    "OPERATORS",
    "get_operator",
    "compare",

    # 聚合函数
    "AGGREGATORS",
    "get_aggregator",
    "aggregate",
]
