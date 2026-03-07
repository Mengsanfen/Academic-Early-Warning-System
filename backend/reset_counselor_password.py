"""
重置辅导员密码脚本
"""
import sys
sys.path.append('.')

from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def reset_counselor_password():
    db = SessionLocal()
    try:
        # 查找辅导员用户
        counselor = db.query(User).filter(User.username == "counselor").first()
        
        if not counselor:
            print("未找到辅导员用户，正在创建...")
            counselor = User(
                username="counselor",
                password_hash=get_password_hash("123456"),
                role="counselor",
                is_active=True,
                nickname="辅导员"
            )
            db.add(counselor)
            db.commit()
            print("辅导员用户创建成功！")
        else:
            # 重置密码
            counselor.password_hash = get_password_hash("123456")
            db.commit()
            print(f"辅导员密码已重置为: 123456")
            print(f"用户ID: {counselor.id}")
            print(f"管理的班级: {counselor.managed_class_ids}")
        
    except Exception as e:
        print(f"错误: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_counselor_password()
