"""
规则引擎 - 聚合函数定义
"""
from typing import Any, Callable, List
from statistics import mean


# 聚合函数映射表
AGGREGATORS: dict[str, Callable[[List[Any]], Any]] = {
    # 计数
    "count": lambda data: len(data),

    # 求和
    "sum": lambda data: sum(float(x) for x in data) if data else 0,

    # 平均值
    "avg": lambda data: mean(float(x) for x in data) if data else 0,

    # 最大值
    "max": lambda data: max(float(x) for x in data) if data else None,

    # 最小值
    "min": lambda data: min(float(x) for x in data) if data else None,

    # 比率（计算True的比例）
    "rate": lambda data: sum(1 for x in data if x) / len(data) if data else 0,

    # 去重计数
    "distinct_count": lambda data: len(set(data)),

    # 首个值
    "first": lambda data: data[0] if data else None,

    # 最后一个值
    "last": lambda data: data[-1] if data else None,
}


def get_aggregator(name: str) -> Callable[[List[Any]], Any]:
    """
    获取聚合函数

    Args:
        name: 聚合函数名称

    Returns:
        聚合函数

    Raises:
        ValueError: 聚合函数不存在
    """
    if name not in AGGREGATORS:
        raise ValueError(f"未知的聚合函数: {name}")
    return AGGREGATORS[name]


def aggregate(name: str, data: List[Any]) -> Any:
    """
    执行聚合计算

    Args:
        name: 聚合函数名称
        data: 数据列表

    Returns:
        聚合结果
    """
    aggregator_func = get_aggregator(name)
    return aggregator_func(data)
