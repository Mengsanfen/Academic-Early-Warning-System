"""
数据模拟模块

为学业预警系统生成符合业务规律的模拟测试数据

主要功能：
1. 生成学院、班级、学生基础数据
2. 根据学生画像生成成绩数据（正态分布）
3. 根据学生画像生成考勤数据（概率分布）
4. 生成预设的预警规则和管理员账号

学生画像分布：
- 优秀学生 (20%): 高分高出勤
- 普通学生 (50%): 中等成绩正常出勤
- 边缘学生 (20%): 低分边缘出勤
- 高危学生 (10%): 低分低出勤

使用示例:
    from app.core.data_simulation import DataSimulator, create_simulator

    # 创建模拟器
    simulator = create_simulator(db)

    # 一键生成所有数据
    results = simulator.generate_all()

    # 查看统计
    stats = simulator.get_statistics()

    # 清空数据
    simulator.clear_all()
"""
from app.core.data_simulation.config import (
    SimulationConfig,
    StudentProfile,
    ProfileConfig,
    ScoreDistribution,
    AttendanceDistribution,
    PROFILE_CONFIGS,
    COURSE_TEMPLATES
)
from app.core.data_simulation.student_generator import StudentGenerator
from app.core.data_simulation.score_generator import ScoreGenerator
from app.core.data_simulation.attendance_generator import AttendanceGenerator
from app.core.data_simulation.simulator import DataSimulator, create_simulator


__all__ = [
    # 主模拟器
    "DataSimulator",
    "create_simulator",

    # 配置类
    "SimulationConfig",
    "StudentProfile",
    "ProfileConfig",
    "ScoreDistribution",
    "AttendanceDistribution",
    "PROFILE_CONFIGS",
    "COURSE_TEMPLATES",

    # 生成器
    "StudentGenerator",
    "ScoreGenerator",
    "AttendanceGenerator",
]
