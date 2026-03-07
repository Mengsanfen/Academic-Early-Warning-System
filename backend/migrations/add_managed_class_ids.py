"""
数据库迁移脚本：添加 managed_class_ids 字段到 users 表

执行方法:
    python migrations/add_managed_class_ids.py
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """执行数据库迁移"""
    db = SessionLocal()

    try:
        # 检查字段是否已存在
        check_sql = text("""
            SELECT COUNT(*) as cnt
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'users'
            AND column_name = 'managed_class_ids'
        """)

        result = db.execute(check_sql).fetchone()

        if result[0] > 0:
            logger.info("字段 managed_class_ids 已存在，无需迁移")
            return

        # 添加字段
        add_column_sql = text("""
            ALTER TABLE users
            ADD COLUMN managed_class_ids TEXT NULL
            COMMENT '管理的班级ID列表(逗号分隔)'
        """)

        db.execute(add_column_sql)
        db.commit()

        logger.info("✅ 成功添加 managed_class_ids 字段到 users 表")

        # 为测试账号设置管理班级（示例）
        sample_data = text("""
            UPDATE users
            SET managed_class_ids = '1,2,3'
            WHERE role = 'counselor' AND managed_class_ids IS NULL
            LIMIT 5
        """)
        db.execute(sample_data)
        db.commit()

        logger.info("✅ 已为现有辅导员账号设置示例管理班级")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 迁移失败: {e}")
        raise
    finally:
        db.close()


def rollback():
    """回滚迁移"""
    db = SessionLocal()

    try:
        rollback_sql = text("""
            ALTER TABLE users
            DROP COLUMN IF EXISTS managed_class_ids
        """)

        db.execute(rollback_sql)
        db.commit()

        logger.info("✅ 成功回滚 managed_class_ids 字段")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 回滚失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移脚本")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="回滚迁移"
    )

    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
