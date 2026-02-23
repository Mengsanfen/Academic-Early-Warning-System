"""
规则引擎 - 操作符定义
"""
from typing import Any, Callable


# 操作符映射表
OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    # 相等比较
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,

    # 数值比较
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,

    # 包含关系
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    "contains": lambda a, b: b in a,

    # 字符串匹配
    "starts_with": lambda a, b: str(a).startswith(str(b)),
    "ends_with": lambda a, b: str(a).endswith(str(b)),
    "like": lambda a, b: str(b).lower() in str(a).lower(),
}


def get_operator(op: str) -> Callable[[Any, Any], bool]:
    """
    获取操作符函数

    Args:
        op: 操作符名称

    Returns:
        操作符函数

    Raises:
        ValueError: 操作符不存在
    """
    if op not in OPERATORS:
        raise ValueError(f"未知的操作符: {op}")
    return OPERATORS[op]


def compare(op: str, left: Any, right: Any) -> bool:
    """
    执行比较操作

    Args:
        op: 操作符
        left: 左操作数
        right: 右操作数

    Returns:
        比较结果
    """
    operator_func = get_operator(op)
    return operator_func(left, right)
