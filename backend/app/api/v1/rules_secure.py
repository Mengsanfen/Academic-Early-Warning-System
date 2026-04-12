"""
规则管理 API（修复版）
"""
from typing import Any, Dict, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.database import get_db
from app.models.rule import (
    AlertLevel,
    COMPREHENSIVE_RULE_CODE,
    COMPREHENSIVE_RULE_MODE,
    Rule,
    RuleType,
)
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class RuleCreate(BaseModel):
    name: str
    code: str
    type: RuleType
    conditions: Dict[str, Any]
    level: AlertLevel
    description: Optional[str] = None
    message_template: Optional[str] = None
    is_active: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    level: Optional[AlertLevel] = None
    description: Optional[str] = None
    message_template: Optional[str] = None
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    id: int
    name: str
    code: str
    type: RuleType
    conditions: Dict[str, Any]
    level: AlertLevel
    description: Optional[str]
    message_template: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


DEFAULT_RULES = [
    {
        "name": "单科成绩不及格预警",
        "code": "SCORE_FAIL",
        "type": RuleType.SCORE,
        "conditions": {"metric": "score", "operator": "<", "threshold": 60},
        "level": AlertLevel.WARNING,
        "description": "单科成绩低于 60 分",
        "message_template": "学生{student_name}({student_no})单科成绩不及格，当前成绩 {metric_value} 分",
    },
    {
        "name": "多门挂科预警",
        "code": "MULTI_FAIL",
        "type": RuleType.SCORE,
        "conditions": {"metric": "fail_count", "operator": ">=", "threshold": 3},
        "level": AlertLevel.SERIOUS,
        "description": "累计挂科 3 门及以上",
        "message_template": "学生{student_name}({student_no})累计挂科 {metric_value} 门",
    },
    {
        "name": "GPA 过低预警",
        "code": "LOW_GPA",
        "type": RuleType.SCORE,
        "conditions": {"metric": "gpa", "operator": "<", "threshold": 2.0},
        "level": AlertLevel.SERIOUS,
        "description": "GPA 低于 2.0",
        "message_template": "学生{student_name}({student_no})GPA 过低，当前 GPA 为 {metric_value}",
    },
    {
        "name": "缺勤过多预警",
        "code": "HIGH_ABSENCE",
        "type": RuleType.ATTENDANCE,
        "conditions": {
            "metric": "absence_count",
            "operator": ">=",
            "threshold": 5,
            "time_window": "1个月",
        },
        "level": AlertLevel.WARNING,
        "description": "1 个月内缺勤 5 次及以上",
        "message_template": "学生{student_name}({student_no})近 1 个月缺勤 {metric_value} 次",
    },
    {
        "name": "出勤率过低预警",
        "code": "LOW_ATTENDANCE",
        "type": RuleType.ATTENDANCE,
        "conditions": {"metric": "attendance_rate", "operator": "<", "threshold": 0.8},
        "level": AlertLevel.SERIOUS,
        "description": "出勤率低于 80%",
        "message_template": "学生{student_name}({student_no})出勤率过低，当前出勤率 {metric_value}",
    },
    {
        "name": "学业综合风险预警",
        "code": COMPREHENSIVE_RULE_CODE,
        "type": RuleType.GRADUATION,
        "conditions": {
            "mode": COMPREHENSIVE_RULE_MODE,
            "fail_count_threshold": 2,
            "absence_count_threshold": 3,
        },
        "level": AlertLevel.URGENT,
        "description": "单学期不及格课程数达到 2 门且累计缺勤次数达到 3 次",
        "message_template": "综合风险：该生已挂科 {fail_count} 门，且缺勤 {absence_count} 次，请立即干预！",
    },
]


@router.get("", response_model=dict, summary="获取规则列表")
def get_rules(
    page: int = 1,
    page_size: int = 20,
    type: Optional[RuleType] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    query = db.query(Rule)

    if type:
        query = query.filter(Rule.type == type)
    if is_active is not None:
        query = query.filter(Rule.is_active == is_active)

    total = query.count()
    rules = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [RuleResponse.model_validate(rule) for rule in rules],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=RuleResponse, summary="创建规则")
def create_rule(
    data: RuleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    if db.query(Rule).filter(Rule.code == data.code).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="规则编码已存在")

    try:
        _validate_conditions(data.conditions)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"规则条件格式错误: {exc}",
        ) from exc

    rule = Rule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.get("/{rule_id}", response_model=RuleResponse, summary="获取规则详情")
def get_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")
    return RuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=RuleResponse, summary="更新规则")
def update_rule(
    rule_id: int,
    data: RuleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")

    if data.conditions is not None:
        try:
            _validate_conditions(data.conditions)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"规则条件格式错误: {exc}",
            ) from exc

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.delete("/{rule_id}", summary="删除规则")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")

    db.delete(rule)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{rule_id}/toggle", response_model=RuleResponse, summary="切换规则启用状态")
def toggle_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")

    rule.is_active = not rule.is_active
    db.commit()
    db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.post("/execute", summary="手动执行规则")
def execute_rules(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    from app.core.rule_engine.simple_engine import SimpleRuleEngine

    try:
        engine = SimpleRuleEngine(db)
        result = engine.execute_all_rules()
        message_parts = [
            f"检查了 {result['total_students']} 名学生",
            f"执行了 {result['total_rules']} 条规则",
            f"触发了 {result['total_triggered']} 次预警",
            f"创建了 {result['alerts_created']} 条新预警",
        ]
        if result["errors"]:
            message_parts.append(f"遇到 {len(result['errors'])} 个错误")

        return {
            "success": True,
            "message": "；".join(message_parts),
            "stats": result,
        }
    except Exception as exc:
        logger.exception("规则执行失败")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"规则执行失败: {exc}",
        ) from exc


@router.post("/init-default", summary="初始化默认规则")
def init_default_rules(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    created_count = 0
    skipped_count = 0

    for rule_data in DEFAULT_RULES:
        existing = db.query(Rule).filter(Rule.code == rule_data["code"]).first()
        if existing:
            skipped_count += 1
            continue

        db.add(Rule(**rule_data))
        created_count += 1

    db.commit()
    return {
        "message": f"初始化完成：创建 {created_count} 条规则，跳过 {skipped_count} 条已存在规则",
        "created": created_count,
        "skipped": skipped_count,
    }


@router.get("/templates", summary="获取规则模板")
def get_rule_templates():
    return {
        "metrics": [
            {"value": "score", "label": "单科成绩", "description": "最新一门课程的成绩"},
            {"value": "avg_score", "label": "平均成绩", "description": "所有课程的平均分"},
            {"value": "fail_count", "label": "挂科门数", "description": "成绩低于 60 分的课程数量"},
            {"value": "gpa", "label": "GPA 绩点", "description": "标准 4.0 制绩点"},
            {"value": "attendance_rate", "label": "出勤率", "description": "正常出勤的比例（0-1）"},
            {"value": "absence_count", "label": "缺勤次数", "description": "旷课的总次数"},
            {"value": "late_count", "label": "迟到次数", "description": "迟到的总次数"},
        ],
        "operators": [
            {"value": "<", "label": "小于"},
            {"value": "<=", "label": "小于等于"},
            {"value": ">", "label": "大于"},
            {"value": ">=", "label": "大于等于"},
            {"value": "==", "label": "等于"},
            {"value": "!=", "label": "不等于"},
        ],
        "time_windows": [
            {"value": None, "label": "全部时间"},
            {"value": "1周", "label": "最近 1 周"},
            {"value": "2周", "label": "最近 2 周"},
            {"value": "1个月", "label": "最近 1 个月"},
            {"value": "3个月", "label": "最近 3 个月"},
            {"value": "1学期", "label": "最近 1 学期"},
            {"value": "1学年", "label": "最近 1 学年"},
        ],
        "examples": DEFAULT_RULES,
        "special_modes": [
            {
                "value": COMPREHENSIVE_RULE_MODE,
                "label": "综合风险",
                "description": "单学期挂科门数和累计缺勤次数联合判定",
            }
        ],
    }


def _validate_conditions(conditions: Dict[str, Any]) -> bool:
    if not isinstance(conditions, dict):
        raise ValueError("条件必须是字典格式")

    if conditions.get("mode") == COMPREHENSIVE_RULE_MODE:
        required_fields = ("fail_count_threshold", "absence_count_threshold")
        for field in required_fields:
            if field not in conditions:
                raise ValueError(f"缺少 '{field}' 字段")
            try:
                value = int(conditions[field])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field} 必须是数字: {conditions[field]}") from exc
            if value < 0:
                raise ValueError(f"{field} 不能小于 0")
        return True

    if "metric" not in conditions:
        raise ValueError("缺少 'metric' 字段")
    if "threshold" not in conditions:
        raise ValueError("缺少 'threshold' 字段")

    valid_metrics = {
        "score",
        "avg_score",
        "fail_count",
        "gpa",
        "attendance_rate",
        "absence_count",
        "late_count",
    }
    if conditions["metric"] not in valid_metrics:
        raise ValueError(f"不支持的指标类型: {conditions['metric']}，支持: {valid_metrics}")

    try:
        float(conditions["threshold"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"阈值必须是数字: {conditions['threshold']}") from exc

    if "operator" in conditions:
        valid_operators = {"<", "<=", ">", ">=", "==", "!="}
        if conditions["operator"] not in valid_operators:
            raise ValueError(f"不支持的运算符: {conditions['operator']}，支持: {valid_operators}")

    return True
