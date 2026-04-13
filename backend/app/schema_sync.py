"""
Runtime schema sync helpers for existing databases.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


logger = logging.getLogger(__name__)


def _existing_columns(engine: Engine, table_name: str) -> set[str]:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _run_alter_statements(engine: Engine, statements: Iterable[str]) -> None:
    sql_list = [statement for statement in statements if statement]
    if not sql_list:
        return

    with engine.begin() as connection:
        for statement in sql_list:
            logger.info("Applying runtime schema update: %s", statement)
            connection.execute(text(statement))


def ensure_runtime_schema(engine: Engine) -> None:
    """
    Add columns that `create_all()` cannot retrofit onto existing tables.
    """
    user_columns = _existing_columns(engine, "users")
    alert_columns = _existing_columns(engine, "alerts")
    rule_columns = _existing_columns(engine, "rules")
    course_columns = _existing_columns(engine, "courses")

    statements: list[str] = []
    json_type = "JSON" if engine.dialect.name.startswith("mysql") else "TEXT"

    if user_columns and "managed_class_ids" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN managed_class_ids TEXT NULL")

    if alert_columns:
        if "student_feedback" not in alert_columns:
            statements.append("ALTER TABLE alerts ADD COLUMN student_feedback TEXT NULL")
        if "feedback_time" not in alert_columns:
            statements.append("ALTER TABLE alerts ADD COLUMN feedback_time DATETIME NULL")

    if rule_columns:
        if "target_type" not in rule_columns:
            statements.append("ALTER TABLE rules ADD COLUMN target_type VARCHAR(20) NOT NULL DEFAULT 'all'")
        if "target_grades" not in rule_columns:
            statements.append(f"ALTER TABLE rules ADD COLUMN target_grades {json_type} NULL")
        if "target_classes" not in rule_columns:
            statements.append(f"ALTER TABLE rules ADD COLUMN target_classes {json_type} NULL")

    if course_columns:
        if "teacher_name" not in course_columns:
            statements.append("ALTER TABLE courses ADD COLUMN teacher_name VARCHAR(50) NULL")
        if "course_type" not in course_columns:
            statements.append("ALTER TABLE courses ADD COLUMN course_type VARCHAR(20) NOT NULL DEFAULT 'required'")

    _run_alter_statements(engine, statements)

    data_fix_statements: list[str] = []
    if rule_columns:
        data_fix_statements.append(
            "UPDATE rules SET target_type = 'all' WHERE target_type IS NULL OR target_type = ''"
        )
    if course_columns:
        data_fix_statements.append(
            "UPDATE courses SET course_type = 'required' WHERE course_type IS NULL OR course_type = ''"
        )

    _run_alter_statements(engine, data_fix_statements)
