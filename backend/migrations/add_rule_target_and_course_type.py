"""
数据库迁移脚本：添加规则目标范围字段和课程类型字段

执行方法:
    python migrations/add_rule_target_and_course_type.py
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
        # ==================== 规则表迁移 ====================
        # 检查 target_type 字段是否已存在
        check_rule_target_type = text("""
            SELECT COUNT(*) as cnt
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'rules'
            AND column_name = 'target_type'
        """)

        result = db.execute(check_rule_target_type).fetchone()

        if result[0] == 0:
            # 添加 target_type 字段
            db.execute(text("""
                ALTER TABLE rules
                ADD COLUMN target_type VARCHAR(20) NOT NULL DEFAULT 'all'
                COMMENT '目标类型: all-全部, grades-按年级, classes-按班级'
            """))
            logger.info("✅ 成功添加 target_type 字段到 rules 表")
        else:
            logger.info("字段 target_type 已存在，跳过")

        # 检查 target_grades 字段是否已存在
        check_target_grades = text("""
            SELECT COUNT(*) as cnt
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'rules'
            AND column_name = 'target_grades'
        """)

        result = db.execute(check_target_grades).fetchone()

        if result[0] == 0:
            # 添加 target_grades 字段
            db.execute(text("""
                ALTER TABLE rules
                ADD COLUMN target_grades JSON NULL
                COMMENT '目标年级列表'
            """))
            logger.info("✅ 成功添加 target_grades 字段到 rules 表")
        else:
            logger.info("字段 target_grades 已存在，跳过")

        # 检查 target_classes 字段是否已存在
        check_target_classes = text("""
            SELECT COUNT(*) as cnt
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'rules'
            AND column_name = 'target_classes'
        """)

        result = db.execute(check_target_classes).fetchone()

        if result[0] == 0:
            # 添加 target_classes 字段
            db.execute(text("""
                ALTER TABLE rules
                ADD COLUMN target_classes JSON NULL
                COMMENT '目标班级ID列表'
            """))
            logger.info("✅ 成功添加 target_classes 字段到 rules 表")
        else:
            logger.info("字段 target_classes 已存在，跳过")

        # ==================== 课程表迁移 ====================
        # 检查 course_type 字段是否已存在
        check_course_type = text("""
            SELECT COUNT(*) as cnt
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'courses'
            AND column_name = 'course_type'
        """)

        result = db.execute(check_course_type).fetchone()

        if result[0] == 0:
            # 添加 course_type 字段
            db.execute(text("""
                ALTER TABLE courses
                ADD COLUMN course_type VARCHAR(20) NOT NULL DEFAULT 'required'
                COMMENT '课程类型: required-必修, elective-选修, public-公共, professional-专业, practice-实践'
            """))
            logger.info("✅ 成功添加 course_type 字段到 courses 表")

            # 为现有课程设置默认类型
            db.execute(text("""
                UPDATE courses
                SET course_type = 'required'
                WHERE course_type IS NULL OR course_type = ''
            """))
            logger.info("✅ 已为现有课程设置默认类型为必修课")
        else:
            logger.info("字段 course_type 已存在，跳过")

        db.commit()
        logger.info("=" * 50)
        logger.info("✅ 数据库迁移完成！")
        logger.info("   - 规则表新增字段: target_type, target_grades, target_classes")
        logger.info("   - 课程表新增字段: course_type")
        logger.info("=" * 50)

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
        # 回滚规则表字段
        db.execute(text("ALTER TABLE rules DROP COLUMN IF EXISTS target_type"))
        db.execute(text("ALTER TABLE rules DROP COLUMN IF EXISTS target_grades"))
        db.execute(text("ALTER TABLE rules DROP COLUMN IF EXISTS target_classes"))
        logger.info("✅ 成功回滚 rules 表字段")

        # 回滚课程表字段
        db.execute(text("ALTER TABLE courses DROP COLUMN IF EXISTS course_type"))
        logger.info("✅ 成功回滚 courses 表字段")

        db.commit()
        logger.info("✅ 回滚完成")

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
