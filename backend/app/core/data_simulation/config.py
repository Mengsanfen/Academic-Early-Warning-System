"""
数据模拟 - 配置参数

定义模拟数据的生成规则和分布参数
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from enum import Enum


class StudentProfile(str, Enum):
    """学生画像类型"""
    EXCELLENT = "excellent"      # 优秀学生（20%）
    NORMAL = "normal"            # 普通学生（50%）
    EDGE = "edge"                # 边缘学生（20%）
    RISK = "risk"                # 高危学生（10%）


@dataclass
class ScoreDistribution:
    """成绩分布参数"""
    mean: float              # 平均分
    std_dev: float           # 标准差
    min_score: float = 0     # 最低分
    max_score: float = 100   # 最高分

    def to_dict(self) -> Dict[str, float]:
        return {
            "mean": self.mean,
            "std_dev": self.std_dev,
            "min_score": self.min_score,
            "max_score": self.max_score
        }


@dataclass
class AttendanceDistribution:
    """考勤分布参数"""
    present_rate: float      # 出勤率
    late_rate: float         # 迟到率
    leave_rate: float        # 请假率
    absent_rate: float       # 旷课率

    def __post_init__(self):
        # 确保总和为1
        total = self.present_rate + self.late_rate + self.leave_rate + self.absent_rate
        if abs(total - 1.0) > 0.001:
            # 归一化
            self.present_rate /= total
            self.late_rate /= total
            self.leave_rate /= total
            self.absent_rate /= total

    def to_dict(self) -> Dict[str, float]:
        return {
            "present_rate": self.present_rate,
            "late_rate": self.late_rate,
            "leave_rate": self.leave_rate,
            "absent_rate": self.absent_rate
        }


@dataclass
class ProfileConfig:
    """学生画像配置"""
    profile: StudentProfile
    score_distribution: ScoreDistribution
    attendance_distribution: AttendanceDistribution
    description: str = ""


# 预定义的学生画像配置
PROFILE_CONFIGS: Dict[StudentProfile, ProfileConfig] = {
    StudentProfile.EXCELLENT: ProfileConfig(
        profile=StudentProfile.EXCELLENT,
        score_distribution=ScoreDistribution(
            mean=88,
            std_dev=6,
            min_score=75,
            max_score=100
        ),
        attendance_distribution=AttendanceDistribution(
            present_rate=0.92,
            late_rate=0.05,
            leave_rate=0.02,
            absent_rate=0.01
        ),
        description="优秀学生：成绩优异，出勤率高"
    ),

    StudentProfile.NORMAL: ProfileConfig(
        profile=StudentProfile.NORMAL,
        score_distribution=ScoreDistribution(
            mean=72,
            std_dev=10,
            min_score=50,
            max_score=95
        ),
        attendance_distribution=AttendanceDistribution(
            present_rate=0.82,
            late_rate=0.10,
            leave_rate=0.05,
            absent_rate=0.03
        ),
        description="普通学生：成绩中等，出勤正常"
    ),

    StudentProfile.EDGE: ProfileConfig(
        profile=StudentProfile.EDGE,
        score_distribution=ScoreDistribution(
            mean=58,
            std_dev=12,
            min_score=30,
            max_score=80
        ),
        attendance_distribution=AttendanceDistribution(
            present_rate=0.70,
            late_rate=0.12,
            leave_rate=0.10,
            absent_rate=0.08
        ),
        description="边缘学生：成绩及格线徘徊，出勤偏低"
    ),

    StudentProfile.RISK: ProfileConfig(
        profile=StudentProfile.RISK,
        score_distribution=ScoreDistribution(
            mean=45,
            std_dev=15,
            min_score=10,
            max_score=70
        ),
        attendance_distribution=AttendanceDistribution(
            present_rate=0.55,
            late_rate=0.15,
            leave_rate=0.15,
            absent_rate=0.15
        ),
        description="高危学生：成绩差，出勤率低"
    ),
}


@dataclass
class SimulationConfig:
    """模拟数据生成总配置"""

    # 学生分布比例
    excellent_ratio: float = 0.20    # 优秀学生比例
    normal_ratio: float = 0.50       # 普通学生比例
    edge_ratio: float = 0.20         # 边缘学生比例
    risk_ratio: float = 0.10         # 高危学生比例

    # 组织结构
    departments: List[str] = field(default_factory=lambda: [
        "计算机科学与技术学院",
        "软件学院",
        "信息工程学院"
    ])

    # 每个学院的班级数量范围
    classes_per_department: Tuple[int, int] = (2, 4)

    # 每个班级的学生数量范围
    students_per_class: Tuple[int, int] = (30, 45)

    # 课程配置
    courses_per_semester: int = 6     # 每学期课程数
    total_semesters: int = 2          # 总学期数

    # 考勤配置
    attendance_weeks: int = 16        # 考勤周数
    attendance_per_week: int = 2      # 每周考勤次数

    # 随机种子（用于可复现）
    random_seed: int = 42

    def __post_init__(self):
        # 验证比例总和
        total = self.excellent_ratio + self.normal_ratio + self.edge_ratio + self.risk_ratio
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"学生比例总和必须为1，当前为{total}")

    def get_profile_distribution(self) -> Dict[StudentProfile, float]:
        """获取学生画像分布"""
        return {
            StudentProfile.EXCELLENT: self.excellent_ratio,
            StudentProfile.NORMAL: self.normal_ratio,
            StudentProfile.EDGE: self.edge_ratio,
            StudentProfile.RISK: self.risk_ratio,
        }


# 课程模板
COURSE_TEMPLATES: List[Dict[str, Any]] = [
    {"name": "高等数学", "credit": 4, "type": "必修", "difficulty": 0.8},
    {"name": "线性代数", "credit": 3, "type": "必修", "difficulty": 0.7},
    {"name": "概率论与数理统计", "credit": 3, "type": "必修", "difficulty": 0.75},
    {"name": "程序设计基础", "credit": 4, "type": "必修", "difficulty": 0.6},
    {"name": "数据结构与算法", "credit": 4, "type": "必修", "difficulty": 0.75},
    {"name": "计算机网络", "credit": 3, "type": "必修", "difficulty": 0.65},
    {"name": "操作系统", "credit": 4, "type": "必修", "difficulty": 0.8},
    {"name": "数据库原理", "credit": 3, "type": "必修", "difficulty": 0.65},
    {"name": "软件工程", "credit": 3, "type": "必修", "difficulty": 0.6},
    {"name": "人工智能导论", "credit": 2, "type": "选修", "difficulty": 0.55},
    {"name": "机器学习", "credit": 3, "type": "选修", "difficulty": 0.85},
    {"name": "Web前端开发", "credit": 3, "type": "选修", "difficulty": 0.5},
    {"name": "Python程序设计", "credit": 2, "type": "选修", "difficulty": 0.45},
    {"name": "大学英语", "credit": 2, "type": "必修", "difficulty": 0.5},
    {"name": "大学物理", "credit": 3, "type": "必修", "difficulty": 0.7},
]

# 常用姓氏
COMMON_SURNAMES: List[str] = [
    "王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴",
    "徐", "孙", "马", "胡", "朱", "郭", "何", "罗", "高", "林"
]

# 常用名字
COMMON_GIVEN_NAMES: List[str] = [
    "伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "军",
    "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "秀兰", "霞",
    "平", "刚", "桂英", "文", "华", "建国", "佳", "鑫", "晶", "欣",
    "宇", "浩", "然", "思", "雨", "梦", "婷", "莉", "博", "昊"
]
