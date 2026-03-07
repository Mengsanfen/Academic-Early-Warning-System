"""
数据模拟 - 成绩数据生成器

根据学生画像生成符合分布规律的成绩数据
"""
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.data_simulation.config import (
    SimulationConfig,
    StudentProfile,
    PROFILE_CONFIGS,
    COURSE_TEMPLATES
)


class ScoreGenerator:
    """成绩数据生成器"""

    def __init__(self, db: Session, config: Optional[SimulationConfig] = None):
        self.db = db
        self.config = config or SimulationConfig()
        self._setup_random()

    def _setup_random(self):
        """设置随机种子"""
        random.seed(self.config.random_seed)

    def generate_courses(self) -> List[Any]:
        """
        生成课程数据

        Returns:
            课程列表
        """
        from app.models.course import Course

        courses = []
        for idx, template in enumerate(COURSE_TEMPLATES):
            course = Course(
                course_code=f"CS{idx+1:03d}",
                course_name=template["name"],
                credit=template["credit"],
                semester="2024-2025-1",
                teacher_name=f"教师{idx+1}"
            )
            self.db.add(course)
            courses.append(course)

        self.db.flush()
        return courses

    def generate_scores(self, students: List[Any], courses: List[Any],
                        semester: int = 1) -> Dict[str, Any]:
        """
        为学生生成成绩数据

        Args:
            students: 学生列表
            courses: 课程列表
            semester: 学期（1或2）

        Returns:
            生成统计信息
        """
        from app.models.score import Score

        stats = {
            "total_scores": 0,
            "pass_count": 0,
            "fail_count": 0,
            "average_score": 0,
            "by_profile": {}
        }

        all_scores = []

        # 选择本学期的课程
        courses_this_semester = self._select_courses_for_semester(courses, semester)

        for student in students:
            profile = self._get_student_profile(student)
            profile_config = PROFILE_CONFIGS.get(profile, PROFILE_CONFIGS[StudentProfile.NORMAL])

            for course in courses_this_semester:
                score = self._generate_score_for_student(
                    student, course, profile_config, semester
                )
                self.db.add(score)
                all_scores.append(score)

                stats["total_scores"] += 1
                if score.score >= 60:
                    stats["pass_count"] += 1
                else:
                    stats["fail_count"] += 1

                # 按画像统计
                profile_key = profile.value if hasattr(profile, 'value') else profile
                if profile_key not in stats["by_profile"]:
                    stats["by_profile"][profile_key] = {"count": 0, "total": 0, "avg": 0}
                stats["by_profile"][profile_key]["count"] += 1
                stats["by_profile"][profile_key]["total"] += score.score

        self.db.flush()

        # 计算平均分
        if all_scores:
            stats["average_score"] = round(
                sum(float(s.score) for s in all_scores) / len(all_scores), 2
            )

        # 计算各画像平均分
        for profile_key in stats["by_profile"]:
            data = stats["by_profile"][profile_key]
            data["avg"] = round(data["total"] / data["count"], 2) if data["count"] > 0 else 0

        return stats

    def _select_courses_for_semester(self, courses: List[Any], semester: int) -> List[Any]:
        """选择本学期的课程"""
        # 每学期选择固定数量的课程
        num_courses = min(self.config.courses_per_semester, len(courses))

        # 根据学期选择不同课程
        start_idx = (semester - 1) * num_courses
        end_idx = start_idx + num_courses

        if end_idx <= len(courses):
            return courses[start_idx:end_idx]
        else:
            # 如果不够，随机选择
            return random.sample(courses, num_courses)

    def _get_student_profile(self, student: Any) -> StudentProfile:
        """获取学生画像"""
        profile_value = getattr(student, 'profile', 'normal')
        if isinstance(profile_value, str):
            try:
                return StudentProfile(profile_value)
            except ValueError:
                return StudentProfile.NORMAL
        return profile_value or StudentProfile.NORMAL

    def _generate_score_for_student(self, student: Any, course: Any,
                                    profile_config: Any, semester: int) -> Any:
        """
        为单个学生生成单科成绩

        Args:
            student: 学生对象
            course: 课程对象
            profile_config: 画像配置
            semester: 学期

        Returns:
            成绩对象
        """
        from app.models.score import Score

        score_dist = profile_config.score_distribution

        # 生成总成绩（基于正态分布）
        total_score = self._generate_normal_score(
            mean=score_dist.mean,
            std_dev=score_dist.std_dev,
            min_val=score_dist.min_score,
            max_val=score_dist.max_score
        )

        # 调整成绩（考虑课程难度）
        difficulty = self._get_course_difficulty(course.course_name)
        difficulty_adjustment = (difficulty - 0.6) * 10  # 难度影响±4分
        total_score = max(0, min(100, total_score - difficulty_adjustment))

        # 确保整数或一位小数
        total_score = round(total_score, 1)

        return Score(
            student_id=student.id,
            course_id=course.id,
            score=total_score,
            semester=f"2024-2025-{semester}",
            exam_type="期末"
        )

    def _generate_normal_score(self, mean: float, std_dev: float,
                                min_val: float, max_val: float) -> float:
        """生成符合正态分布的成绩"""
        # 使用Box-Muller变换生成正态分布随机数
        u1 = random.random()
        u2 = random.random()

        # 避免log(0)
        u1 = max(u1, 1e-10)

        z = (-2 * math.log(u1)) ** 0.5 * math.cos(2 * math.pi * u2)
        score = mean + z * std_dev

        # 截断到范围内
        return max(min_val, min(max_val, score))

    def _generate_component_score(self, total_score: float,
                                   component: str) -> float:
        """生成成绩组成部分（平时/考试）"""
        if component == "usual":
            # 平时成绩通常较高且波动小
            base = min(95, total_score + 5)
            variation = random.uniform(-5, 5)
        else:
            # 考试成绩波动较大
            base = total_score
            variation = random.uniform(-8, 8)

        score = base + variation
        return round(max(0, min(100, score)), 1)

    def _get_course_difficulty(self, course_name: str) -> float:
        """获取课程难度系数"""
        for template in COURSE_TEMPLATES:
            if template["name"] == course_name:
                return template.get("difficulty", 0.5)
        return 0.5


# 导入math模块（用于正态分布计算）
import math
