"""
数据库初始化脚本

运行方式: python -m app.scripts.init_db
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.database import SessionLocal, engine, Base
from app.core.data_simulation.simulator import DataSimulator, SimulationConfig


def init_database():
    """初始化数据库"""
    print("[*] 开始初始化数据库...")

    # 创建所有表
    print("  [1] 创建数据表...")
    Base.metadata.create_all(bind=engine)
    print("  [OK] 数据表创建完成")

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 创建模拟器（使用默认配置）
        config = SimulationConfig(
            total_semesters=2,  # 学期数量
            random_seed=42  # 随机种子
        )

        simulator = DataSimulator(db, config)

        # 清空旧数据
        print("  [2] 清空旧数据...")
        simulator.clear_all()

        # 生成新数据
        print("  [3] 生成测试数据...")
        results = simulator.generate_all(include_rules=True)

        if results["success"]:
            print("\n[OK] 数据库初始化成功!")
            print("\n测试账号:")
            print("  管理员: admin / admin123")
            print("  辅导员: counselor / counselor123")
        else:
            print(f"\n[ERROR] 初始化失败: {results.get('errors', '未知错误')}")

    except Exception as e:
        print(f"\n[ERROR] 初始化失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
