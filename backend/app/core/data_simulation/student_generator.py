"""
数据模拟 - 学生数据生成器

生成学院、班级、学生等基础数据
"""
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date

from sqlalchemy.orm import Session

from app.core.data_simulation.config import (
    SimulationConfig,
    StudentProfile,
    COMMON_SURNAMES,
    COMMON_GIVEN_NAMES
)


class StudentGenerator:
    """学生数据生成器"""

    def __init__(self, db: Session, config: Optional[SimulationConfig] = None):
        self.db = db
        self.config = config or SimulationConfig()
        self._setup_random()

    def _setup_random(self):
        """设置随机种子"""
        random.seed(self.config.random_seed)

    def generate_all(self) -> Dict[str, Any]:
        """
        生成所有基础数据

        Returns:
            生成统计信息
        """
        stats = {
            "departments": 0,
            "classes": 0,
            "students": 0,
            "profile_distribution": {}
        }

        # 生成学院
        departments = self.generate_departments()
        stats["departments"] = len(departments)

        # 为每个学院生成班级和学生
        for dept in departments:
            classes = self.generate_classes(dept)
            stats["classes"] += len(classes)

            for cls in classes:
                students = self.generate_students(cls)
                stats["students"] += len(students)

                # 统计学生画像分布
                for student in students:
                    profile = student.profile
                    stats["profile_distribution"][profile] = \
                        stats["profile_distribution"].get(profile, 0) + 1

        self.db.commit()
        return stats

    def generate_departments(self) -> List[Any]:
        """生成学院数据"""
        from app.models.student import Department

        departments = []
        for name in self.config.departments:
            dept = Department(name=name)
            self.db.add(dept)
            departments.append(dept)

        self.db.flush()  # 获取ID
        return departments

    def generate_classes(self, department: Any, count: Optional[int] = None) -> List[Any]:
        """
        生成班级数据

        Args:
            department: 所属学院
            count: 班级数量，为空则随机生成

        Returns:
            班级列表
        """
        from app.models.student import Class

        if count is None:
            min_count, max_count = self.config.classes_per_department
            count = random.randint(min_count, max_count)

        classes = []
        current_year = datetime.now().year

        for i in range(count):
            # 生成班级名称（如：2021级计算机1班）
            year = current_year - random.randint(0, 2)  # 大一到大三
            class_no = i + 1
            name = f"{year}级{department.name[:2]}{class_no}班"

            cls = Class(
                name=name,
                department_id=department.id,
                grade=year
            )
            self.db.add(cls)
            classes.append(cls)

        self.db.flush()
        return classes

    def generate_students(self, class_info: Any, count: Optional[int] = None) -> List[Any]:
        """
        生成学生数据

        Args:
            class_info: 所属班级
            count: 学生数量，为空则随机生成

        Returns:
            学生列表
        """
        from app.models.student import Student

        if count is None:
            min_count, max_count = self.config.students_per_class
            count = random.randint(min_count, max_count)

        students = []

        # 计算各画像学生数量
        profile_counts = self._calculate_profile_counts(count)

        # 生成学生
        used_names = set()
        student_index = 1

        for profile, profile_count in profile_counts.items():
            for _ in range(profile_count):
                # 生成唯一学号
                student_no = self._generate_student_no(class_info, student_index)

                # 生成姓名（避免重复）
                name = self._generate_name(used_names)
                used_names.add(name)

                # 生成联系方式
                phone = self._generate_phone()
                email = f"{student_no}@student.edu.cn"

                student = Student(
                    student_no=student_no,
                    name=name,
                    gender=random.choice(["男", "女"]),
                    phone=phone,
                    email=email,
                    class_id=class_info.id,
                    profile=profile.value,
                    is_active=True
                )
                self.db.add(student)
                students.append(student)
                student_index += 1

        self.db.flush()
        return students

    def _calculate_profile_counts(self, total: int) -> Dict[StudentProfile, int]:
        """计算各画像学生数量"""
        distribution = self.config.get_profile_distribution()
        counts = {}

        remaining = total
        profiles = list(distribution.keys())

        for i, profile in enumerate(profiles):
            if i == len(profiles) - 1:
                # 最后一个画像获得剩余所有
                counts[profile] = remaining
            else:
                ratio = distribution[profile]
                count = int(total * ratio)
                counts[profile] = count
                remaining -= count

        return counts

    def _generate_student_no(self, class_info: Any, index: int) -> str:
        """生成学号"""
        # 格式：年份 + 学院代码(2位) + 班级代码(2位) + 序号(2位)
        year = str(class_info.grade)[-2:]
        dept_code = str(class_info.department_id).zfill(2)
        class_code = str(class_info.id % 100).zfill(2)
        seq = str(index).zfill(2)

        return f"{year}{dept_code}{class_code}{seq}"

    def _generate_name(self, used_names: set) -> str:
        """生成随机姓名"""
        attempts = 0
        while attempts < 100:
            surname = random.choice(COMMON_SURNAMES)

            # 随机决定名字长度（1-2个字）
            if random.random() < 0.6:
                given_name = random.choice(COMMON_GIVEN_NAMES)
            else:
                given_name = random.choice(COMMON_GIVEN_NAMES) + \
                           random.choice(COMMON_GIVEN_NAMES)

            name = surname + given_name

            if name not in used_names:
                return name

            attempts += 1

        # 如果100次都没成功，添加随机数字
        return surname + random.choice(COMMON_GIVEN_NAMES) + str(random.randint(1, 99))

    def _generate_phone(self) -> str:
        """生成随机手机号"""
        prefixes = ["138", "139", "150", "151", "152", "186", "187", "188"]
        prefix = random.choice(prefixes)
        suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
        return prefix + suffix

    def assign_profiles(self, student_ids: List[int]) -> Dict[int, str]:
        """
        为已有学生分配画像

        Args:
            student_ids: 学生ID列表

        Returns:
            学生ID -> 画像的映射
        """
        from app.models.student import Student

        total = len(student_ids)
        profile_counts = self._calculate_profile_counts(total)

        assignments = {}
        shuffled_ids = student_ids.copy()
        random.shuffle(shuffled_ids)

        index = 0
        for profile, count in profile_counts.items():
            for _ in range(count):
                if index < len(shuffled_ids):
                    student_id = shuffled_ids[index]
                    assignments[student_id] = profile.value

                    # 更新数据库
                    student = self.db.query(Student).filter(
                        Student.id == student_id
                    ).first()
                    if student:
                        student.profile = profile.value

                    index += 1

        self.db.commit()
        return assignments
