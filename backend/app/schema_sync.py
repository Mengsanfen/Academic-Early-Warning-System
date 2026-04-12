"""
Runtime schema sync helpers for existing databases.
"""
from __future__ import annotations

import logging
from typing import Iterable

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

    statements: list[str] = []

    if user_columns and "managed_class_ids" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN managed_class_ids TEXT NULL")

    if alert_columns:
        if "student_feedback" not in alert_columns:
            statements.append("ALTER TABLE alerts ADD COLUMN student_feedback TEXT NULL")
        if "feedback_time" not in alert_columns:
            statements.append("ALTER TABLE alerts ADD COLUMN feedback_time DATETIME NULL")

    _run_alter_statements(engine, statements)
