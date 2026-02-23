"""
数据初始化脚本

运行此脚本可以：
1. 创建数据库表结构
2. 生成模拟测试数据
3. 创建默认管理员账号

使用方法：
    cd backend
    python scripts/init_data.py
"""
import sys
import os

# 设置控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal, Base
from app.core.data_simulation import DataSimulator, SimulationConfig


def init_database():
    """创建数据库表"""
    print("[*] 创建数据库表...")

    # 导入所有模型以确保它们被注册
    from app.models import base
    from app.models import user
    from app.models import student
    from app.models import course
    from app.models import score
    from app.models import attendance
    from app.models import rule
    from app.models import alert

    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("[OK] 数据库表创建完成")


def init_data(clear_existing: bool = False):
    """
    初始化模拟数据

    Args:
        clear_existing: 是否清空现有数据
    """
    db = SessionLocal()

    try:
        # 创建模拟器
        config = SimulationConfig(
            random_seed=42,  # 固定种子保证可复现
            excellent_ratio=0.20,
            normal_ratio=0.50,
            edge_ratio=0.20,
            risk_ratio=0.10,
        )
        simulator = DataSimulator(db, config)

        # 清空现有数据
        if clear_existing:
            print("[*] 清空现有数据...")
            simulator.clear_all()

        # 生成数据
        results = simulator.generate_all(include_rules=True)

        if results["success"]:
            print("\n[OK] 数据初始化成功!")
            print(f"     耗时: {results['duration']}")
        else:
            print(f"\n[ERROR] 数据初始化失败: {results['errors']}")

    finally:
        db.close()


def show_statistics():
    """显示数据库统计"""
    db = SessionLocal()

    try:
        from app.core.data_simulation import create_simulator
        simulator = create_simulator(db)
        stats = simulator.get_statistics()

        print("\n[统计] 数据库统计:")
        print("-" * 30)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("-" * 30)

    finally:
        db.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="学业预警系统数据初始化")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="清空现有数据后再生成"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="只显示统计信息"
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="只创建数据库表"
    )

    args = parser.parse_args()

    if args.stats:
        show_statistics()
    elif args.init_db:
        init_database()
    else:
        init_database()
        init_data(clear_existing=args.clear)
        show_statistics()


if __name__ == "__main__":
    main()
