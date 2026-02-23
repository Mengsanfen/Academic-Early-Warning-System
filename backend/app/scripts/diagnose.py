"""
诊断脚本 - 检查数据库和用户状态
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models.user import User
from app.core.security import verify_password, get_password_hash


def diagnose():
    print("=" * 50)
    print("诊断学业预警系统登录问题")
    print("=" * 50)

    db = SessionLocal()

    try:
        # 1. 检查数据库连接
        print("\n[1] 检查数据库连接...")
        try:
            db.execute(text("SELECT 1"))
            print("    [OK] 数据库连接正常")
        except Exception as e:
            print(f"    [ERROR] 数据库连接失败: {e}")
            return

        # 2. 检查用户表
        print("\n[2] 检查用户表...")
        users = db.query(User).all()
        print(f"    用户数量: {len(users)}")

        if len(users) == 0:
            print("    [WARNING] 没有用户数据！需要运行初始化脚本")
            print("    运行命令: python -m app.scripts.init_db")
        else:
            print("    用户列表:")
            for u in users:
                print(f"      - ID: {u.id}, 用户名: {u.username}, 角色: {u.role}, 启用: {u.is_active}")
                print(f"        密码哈希前20字符: {u.password_hash[:20]}...")

        # 3. 测试密码验证
        print("\n[3] 测试密码验证...")
        admin = db.query(User).filter(User.username == "admin").first()

        if admin:
            # 测试验证
            test_result = verify_password("admin123", admin.password_hash)
            print(f"    验证 'admin123': {test_result}")

            if not test_result:
                print("    [WARNING] 密码验证失败，正在修复...")
                # 重新生成密码哈希
                new_hash = get_password_hash("admin123")
                admin.password_hash = new_hash
                db.commit()
                print("    [OK] 密码已重置")

                # 再次验证
                test_result = verify_password("admin123", admin.password_hash)
                print(f"    重新验证 'admin123': {test_result}")
        else:
            print("    [ERROR] 找不到 admin 用户！")
            print("    正在创建默认用户...")

            # 创建默认用户
            admin_user = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            counselor_user = User(
                username="counselor",
                password_hash=get_password_hash("counselor123"),
                role="counselor",
                is_active=True
            )
            db.add(admin_user)
            db.add(counselor_user)
            db.commit()
            print("    [OK] 默认用户已创建")

        print("\n" + "=" * 50)
        print("诊断完成！")
        print("测试账号:")
        print("  管理员: admin / admin123")
        print("  辅导员: counselor / counselor123")
        print("=" * 50)

    except Exception as e:
        print(f"\n[ERROR] 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    diagnose()
