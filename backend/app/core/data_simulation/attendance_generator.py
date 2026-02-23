"""
数据模拟 - 考勤数据生成器

根据学生画像生成符合分布规律的考勤数据
"""
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta

from sqlalchemy.orm import Session

from app.core.data_simulation.config import (
    SimulationConfig,
    StudentProfile,
    PROFILE_CONFIGS
)
from app.models.attendance import AttendanceStatus


class AttendanceGenerator:
    """考勤数据生成器"""

    def __init__(self, db: Session, config: Optional[SimulationConfig] = None):
        self.db = db
        self.config = config or SimulationConfig()
        self._setup_random()

    def _setup_random(self):
        """设置随机种子"""
        random.seed(self.config.random_seed)

    def generate_attendance(self, students: List[Any], courses: List[Any],
                            start_date: Optional[date] = None) -> Dict[str, Any]:
        """
        生成考勤数据

        Args:
            students: 学生列表
            courses: 课程列表
            start_date: 考勤开始日期

        Returns:
            生成统计信息
        """
        if start_date is None:
            # 默认从本学期开始
            start_date = date(2024, 9, 1)

        stats = {
            "total_records": 0,
            "by_status": {
                "present": 0,
                "late": 0,
                "leave": 0,
                "absent": 0
            },
            "by_profile": {}
        }

        # 生成考勤日期列表
        attendance_dates = self._generate_attendance_dates(start_date)

        for student in students:
            profile = self._get_student_profile(student)
            profile_config = PROFILE_CONFIGS.get(profile, PROFILE_CONFIGS[StudentProfile.NORMAL])

            # 为每门课程生成考勤记录
            for course in courses[:self.config.courses_per_semester]:
                for attendance_date in attendance_dates:
                    status = self._generate_attendance_status(profile_config)

                    attendance = self._create_attendance_record(
                        student_id=student.id,
                        course_id=course.id,
                        attendance_date=attendance_date,
                        status=status
                    )
                    self.db.add(attendance)

                    stats["total_records"] += 1
                    stats["by_status"][status] += 1

                    # 按画像统计
                    profile_key = profile.value if hasattr(profile, 'value') else profile
                    if profile_key not in stats["by_profile"]:
                        stats["by_profile"][profile_key] = {"total": 0, "absent": 0}
                    stats["by_profile"][profile_key]["total"] += 1
                    if status == "absent":
                        stats["by_profile"][profile_key]["absent"] += 1

        self.db.flush()

        # 计算缺勤率
        total = stats["total_records"]
        if total > 0:
            stats["absence_rate"] = round(stats["by_status"]["absent"] / total, 4)
        else:
            stats["absence_rate"] = 0

        return stats

    def _generate_attendance_dates(self, start_date: date) -> List[date]:
        """
        生成考勤日期列表

        Args:
            start_date: 开始日期

        Returns:
            考勤日期列表
        """
        dates = []
        current_date = start_date

        for week in range(self.config.attendance_weeks):
            for _ in range(self.config.attendance_per_week):
                # 跳过周末
                while current_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
                    current_date += timedelta(days=1)

                dates.append(current_date)
                current_date += timedelta(days=1)

            # 进入下一周
            days_to_monday = (7 - current_date.weekday()) % 7
            if days_to_monday == 0:
                days_to_monday = 7
            current_date += timedelta(days=days_to_monday)

        return dates

    def _get_student_profile(self, student: Any) -> StudentProfile:
        """获取学生画像"""
        profile_value = getattr(student, 'profile', 'normal')
        if isinstance(profile_value, str):
            try:
                return StudentProfile(profile_value)
            except ValueError:
                return StudentProfile.NORMAL
        return profile_value or StudentProfile.NORMAL

    def _generate_attendance_status(self, profile_config: Any) -> str:
        """
        根据画像生成考勤状态

        Args:
            profile_config: 画像配置

        Returns:
            考勤状态字符串
        """
        attendance_dist = profile_config.attendance_distribution

        # 根据概率分布选择状态
        rand = random.random()
        cumulative = 0

        status_map = [
            ("present", attendance_dist.present_rate),
            ("late", attendance_dist.late_rate),
            ("leave", attendance_dist.leave_rate),
            ("absent", attendance_dist.absent_rate),
        ]

        for status, probability in status_map:
            cumulative += probability
            if rand < cumulative:
                return status

        return "present"  # 默认出勤

    def _create_attendance_record(self, student_id: int, course_id: int,
                                   attendance_date: date, status: str) -> Any:
        """创建考勤记录"""
        from app.models.attendance import Attendance

        status_enum = {
            "present": AttendanceStatus.PRESENT,
            "late": AttendanceStatus.LATE,
            "leave": AttendanceStatus.LEAVE,
            "absent": AttendanceStatus.ABSENT
        }

        return Attendance(
            student_id=student_id,
            course_id=course_id,
            date=attendance_date,
            status=status_enum.get(status, AttendanceStatus.PRESENT)
        )

    def generate_continuous_absence_cases(self, students: List[Any],
                                          courses: List[Any],
                                          target_count: int = 5) -> int:
        """
        生成连续缺勤的典型案例（用于测试连续缺勤规则）

        Args:
            students: 学生列表（优先选择高危学生）
            courses: 课程列表
            target_count: 目标案例数量

        Returns:
            实际生成的案例数量
        """
        # 优先选择高危和边缘学生
        priority_students = []
        other_students = []

        for student in students:
            profile = self._get_student_profile(student)
            if profile in [StudentProfile.RISK, StudentProfile.EDGE]:
                priority_students.append(student)
            else:
                other_students.append(student)

        # 打乱顺序
        random.shuffle(priority_students)
        random.shuffle(other_students)

        target_students = (priority_students + other_students)[:target_count]

        generated = 0
        start_date = date(2024, 11, 1)  # 选择一个月生成连续缺勤

        for student in target_students:
            # 随机选择一门课程
            course = random.choice(courses)

            # 生成连续3-7天的缺勤
            consecutive_days = random.randint(3, 7)

            for i in range(consecutive_days):
                attendance_date = start_date + timedelta(days=i)

                # 跳过周末
                if attendance_date.weekday() >= 5:
                    continue

                attendance = self._create_attendance_record(
                    student_id=student.id,
                    course_id=course.id,
                    attendance_date=attendance_date,
                    status="absent"
                )
                self.db.add(attendance)
                generated += 1

        self.db.flush()
        return generated

    def get_attendance_summary(self, student_id: int) -> Dict[str, Any]:
        """
        获取学生考勤统计

        Args:
            student_id: 学生ID

        Returns:
            考勤统计信息
        """
        from app.models.attendance import Attendance

        records = self.db.query(Attendance).filter(
            Attendance.student_id == student_id
        ).all()

        if not records:
            return {"total": 0, "absent_rate": 0}

        status_counts = {
            "present": 0,
            "late": 0,
            "leave": 0,
            "absent": 0
        }

        for record in records:
            status_key = record.status.value if hasattr(record.status, 'value') else str(record.status)
            if status_key in status_counts:
                status_counts[status_key] += 1

        total = len(records)
        absent_rate = round(status_counts["absent"] / total, 4) if total > 0 else 0

        return {
            "total": total,
            "absent_rate": absent_rate,
            "status_counts": status_counts
        }
