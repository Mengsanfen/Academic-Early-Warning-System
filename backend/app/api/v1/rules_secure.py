"""
规则管理 API（修复版）
"""
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.database import get_db
from app.models.rule import (
    AlertLevel,
    COMPREHENSIVE_RULE_CODE,
    COMPREHENSIVE_RULE_MODE,
    Rule,
    RuleType,
    TargetType,
)
from app.models.student import Class
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
    # 目标范围配置
    target_type: TargetType = TargetType.ALL
    target_grades: List[str] = Field(default_factory=list)
    target_classes: List[int] = Field(default_factory=list)


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    level: Optional[AlertLevel] = None
    description: Optional[str] = None
    message_template: Optional[str] = None
    is_active: Optional[bool] = None
    # 目标范围配置
    target_type: Optional[TargetType] = None
    target_grades: Optional[List[str]] = None
    target_classes: Optional[List[int]] = None


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
    # 目标范围配置
    target_type: TargetType
    target_grades: Optional[List[str]]
    target_classes: Optional[List[int]]

    class Config:
        from_attributes = True


def _normalize_target_grades(target_grades: Optional[List[str]]) -> List[str]:
    if not target_grades:
        return []
    normalized = sorted({str(grade).strip() for grade in target_grades if str(grade).strip()})
    return normalized


def _normalize_target_classes(target_classes: Optional[List[int]]) -> List[int]:
    if not target_classes:
        return []
    normalized = sorted({int(class_id) for class_id in target_classes})
    if any(class_id <= 0 for class_id in normalized):
        raise ValueError("班级ID必须为正整数")
    return normalized


def _validate_targets(
    db: Session,
    target_type: TargetType,
    target_grades: Optional[List[str]],
    target_classes: Optional[List[int]],
) -> dict:
    normalized_grades = _normalize_target_grades(target_grades)
    normalized_classes = _normalize_target_classes(target_classes)

    if target_type == TargetType.ALL:
        return {
            "target_type": TargetType.ALL,
            "target_grades": [],
            "target_classes": [],
        }

    if target_type == TargetType.GRADES:
        if not normalized_grades:
            raise ValueError("请选择至少一个实施年级")

        existing_grades = {
            row[0]
            for row in db.query(Class.grade)
            .filter(Class.grade.in_(normalized_grades))
            .distinct()
            .all()
        }
        missing = [grade for grade in normalized_grades if grade not in existing_grades]
        if missing:
            raise ValueError(f"以下年级不存在: {', '.join(missing)}")

        return {
            "target_type": TargetType.GRADES,
            "target_grades": normalized_grades,
            "target_classes": [],
        }

    if target_type == TargetType.CLASSES:
        if not normalized_classes:
            raise ValueError("请选择至少一个实施班级")

        classes = db.query(Class.id).filter(Class.id.in_(normalized_classes)).all()
        existing_ids = {row[0] for row in classes}
        missing = [str(class_id) for class_id in normalized_classes if class_id not in existing_ids]
        if missing:
            raise ValueError(f"以下班级不存在: {', '.join(missing)}")

        return {
            "target_type": TargetType.CLASSES,
            "target_grades": [],
            "target_classes": normalized_classes,
        }

    raise ValueError("不支持的实施对象类型")


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


RULE_METRICS = [
    {
        "value": "score",
        "label": "单科成绩",
        "description": "按最近一次单门成绩触发预警",
        "supports_time_window": True,
        "supports_course_type": True,
        "unit": "分",
    },
    {
        "value": "avg_score",
        "label": "平均成绩",
        "description": "按课程平均成绩触发预警",
        "supports_time_window": True,
        "supports_course_type": True,
        "unit": "分",
    },
    {
        "value": "fail_count",
        "label": "不及格课程数",
        "description": "按不及格课程门数触发预警",
        "supports_time_window": True,
        "supports_course_type": True,
        "unit": "门",
    },
    {
        "value": "gpa",
        "label": "GPA",
        "description": "按 GPA 绩点触发预警",
        "supports_time_window": True,
        "supports_course_type": True,
        "unit": "绩点",
    },
    {
        "value": "earned_credit",
        "label": "已获学分",
        "description": "统计已通过课程获得的学分，可按必修/选修分类",
        "supports_time_window": True,
        "supports_course_type": True,
        "unit": "学分",
    },
    {
        "value": "failed_credit",
        "label": "未获学分",
        "description": "统计当前未通过课程对应的学分，可按必修/选修分类",
        "supports_time_window": True,
        "supports_course_type": True,
        "unit": "学分",
    },
    {
        "value": "attendance_rate",
        "label": "出勤率",
        "description": "按出勤率触发预警，阈值建议填写 0 到 1 之间的小数",
        "supports_time_window": True,
        "supports_course_type": True,
        "unit": "比例",
    },
    {
        "value": "absence_count",
        "label": "缺勤次数",
        "description": "按缺勤次数触发预警",
        "supports_time_window": True,
        "supports_course_type": True,
        "unit": "次",
    },
    {
        "value": "late_count",
        "label": "迟到次数",
        "description": "按迟到次数触发预警",
        "supports_time_window": True,
        "supports_course_type": True,
        "unit": "次",
    },
]

RULE_OPERATORS = [
    {"value": "<", "label": "小于"},
    {"value": "<=", "label": "小于等于"},
    {"value": ">", "label": "大于"},
    {"value": ">=", "label": "大于等于"},
    {"value": "==", "label": "等于"},
    {"value": "!=", "label": "不等于"},
]

RULE_TIME_WINDOWS = [
    {"value": None, "label": "全部时间"},
    {"value": "1w", "label": "最近 1 周"},
    {"value": "2w", "label": "最近 2 周"},
    {"value": "1m", "label": "最近 1 个月"},
    {"value": "3m", "label": "最近 3 个月"},
    {"value": "1term", "label": "最近 1 学期"},
    {"value": "1y", "label": "最近 1 学年"},
]

RULE_TARGET_TYPES = [
    {"value": "all", "label": "全部学生", "description": "规则适用于所有学生"},
    {"value": "grades", "label": "按年级", "description": "规则仅适用于选定年级"},
    {"value": "classes", "label": "按班级", "description": "规则仅适用于选定班级"},
]

RULE_COURSE_TYPES = [
    {"value": "required", "label": "必修课", "description": "核心培养方案中的必修课程"},
    {"value": "elective", "label": "选修课", "description": "学生自主选修课程"},
    {"value": "public", "label": "公共课", "description": "通识或公共基础课程"},
    {"value": "professional", "label": "专业课", "description": "专业核心与专业方向课程"},
    {"value": "practice", "label": "实践课", "description": "实验、实训、实习等实践类课程"},
]

RULE_QUICK_TEMPLATES = [
    {
        "name": "必修学分不足预警",
        "code": "REQUIRED_CREDIT_SHORTAGE",
        "type": RuleType.GRADUATION,
        "level": AlertLevel.SERIOUS,
        "description": "用于识别学生当前已取得必修学分低于培养要求的情况",
        "message_template": "学生{student_name}({student_no})已取得必修学分 {metric_value}，低于要求 {threshold}",
        "target_type": TargetType.ALL,
        "conditions": {
            "metric": "earned_credit",
            "operator": "<",
            "threshold": 30,
            "course_type": "required",
        },
    },
    {
        "name": "选修学分不足预警",
        "code": "ELECTIVE_CREDIT_SHORTAGE",
        "type": RuleType.GRADUATION,
        "level": AlertLevel.WARNING,
        "description": "用于识别学生选修学分累计不足的情况",
        "message_template": "学生{student_name}({student_no})已取得选修学分 {metric_value}，低于要求 {threshold}",
        "target_type": TargetType.ALL,
        "conditions": {
            "metric": "earned_credit",
            "operator": "<",
            "threshold": 8,
            "course_type": "elective",
        },
    },
    {
        "name": "必修不及格课程数预警",
        "code": "REQUIRED_FAIL_COUNT",
        "type": RuleType.SCORE,
        "level": AlertLevel.SERIOUS,
        "description": "用于识别必修课不及格课程门数偏多的学生",
        "message_template": "学生{student_name}({student_no})当前必修不及格课程数为 {metric_value}，达到阈值 {threshold}",
        "target_type": TargetType.ALL,
        "conditions": {
            "metric": "fail_count",
            "operator": ">=",
            "threshold": 2,
            "course_type": "required",
        },
    },
]


def _normalize_target_scope(
    target_type: TargetType,
    target_grades: Optional[List[str]],
    target_classes: Optional[List[int]],
) -> tuple[Optional[List[str]], Optional[List[int]]]:
    if target_type == TargetType.ALL:
        return None, None

    if target_type == TargetType.GRADES:
        grades = sorted({str(item).strip() for item in (target_grades or []) if str(item).strip()})
        if not grades:
            raise ValueError("按年级实施时，必须至少选择一个年级")
        return grades, None

    if target_type == TargetType.CLASSES:
        classes = sorted({int(item) for item in (target_classes or []) if item is not None})
        if not classes:
            raise ValueError("按班级实施时，必须至少选择一个班级")
        return None, classes

    raise ValueError("不支持的实施对象类型")


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
    rules = (
        query.order_by(Rule.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
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
        target_payload = _validate_targets(
            db,
            data.target_type,
            data.target_grades,
            data.target_classes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"规则配置有误: {exc}",
        ) from exc

    payload = data.model_dump()
    payload.update(target_payload)
    rule = Rule(**payload)
    db.add(rule)
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
        "metrics": RULE_METRICS,
        "operators": RULE_OPERATORS,
        "time_windows": RULE_TIME_WINDOWS,
        "examples": DEFAULT_RULES,
        "quick_templates": RULE_QUICK_TEMPLATES,
        "special_modes": [
            {
                "value": COMPREHENSIVE_RULE_MODE,
                "label": "综合风险",
                "description": "单学期挂科门数和累计缺勤次数联合判定",
            }
        ],
        "target_types": RULE_TARGET_TYPES,
        "course_types": RULE_COURSE_TYPES,
    }


@router.get("/grades", summary="获取所有年级列表")
def get_grades(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """获取系统中所有年级列表，用于规则目标选择"""
    from app.models.student import Class
    from sqlalchemy import distinct

    grades = db.query(distinct(Class.grade)).order_by(Class.grade.desc()).all()
    return {
        "items": [{"value": g[0], "label": g[0]} for g in grades if g[0]],
        "total": len(grades)
    }


@router.get("/target-options", summary="获取规则目标选项")
def get_target_options(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """获取规则目标选项（年级和班级列表）"""
    from app.models.student import Class, Department
    from sqlalchemy import distinct

    # 获取所有年级
    grades = db.query(distinct(Class.grade)).order_by(Class.grade.desc()).all()
    grade_list = [g[0] for g in grades if g[0]]

    # 获取所有班级
    classes = db.query(Class).order_by(Class.grade.desc(), Class.name).all()
    class_list = [
        {
            "id": c.id,
            "name": c.name,
            "grade": c.grade,
            "department_name": c.department.name if c.department else None
        }
        for c in classes
    ]

    return {
        "grades": grade_list,
        "classes": class_list
    }



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

    update_payload = data.model_dump(exclude_unset=True)

    try:
        if update_payload.get("conditions") is not None:
            _validate_conditions(update_payload["conditions"])

        target_payload = _validate_targets(
            db,
            update_payload.get("target_type", rule.target_type),
            update_payload.get("target_grades", rule.target_grades),
            update_payload.get("target_classes", rule.target_classes),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"规则配置有误: {exc}",
        ) from exc

    update_payload.update(target_payload)

    for key, value in update_payload.items():
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
        "earned_credit",
        "failed_credit",
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

    if "course_type" in conditions and conditions["course_type"] is not None:
        valid_course_types = {item["value"] for item in RULE_COURSE_TYPES}
        if conditions["course_type"] not in valid_course_types:
            raise ValueError(f"不支持的课程类型: {conditions['course_type']}")

    return True
