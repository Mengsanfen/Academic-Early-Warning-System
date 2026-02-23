"""
数据模拟 - 主模拟器类

整合所有生成器，提供一键数据生成功能
"""
import random
from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.data_simulation.config import SimulationConfig, StudentProfile
from app.core.data_simulation.student_generator import StudentGenerator
from app.core.data_simulation.score_generator import ScoreGenerator
from app.core.data_simulation.attendance_generator import AttendanceGenerator


class DataSimulator:
    """
    数据模拟器主类

    职责：
    1. 协调各个数据生成器
    2. 提供一键生成完整测试数据的功能
    3. 生成预设的预警规则
    4. 提供数据统计和报告功能
    """

    def __init__(self, db: Session, config: Optional[SimulationConfig] = None):
        self.db = db
        self.config = config or SimulationConfig()
        self._reset_generators()

    def _reset_generators(self):
        """重置生成器（应用新的随机种子）"""
        random.seed(self.config.random_seed)
        self.student_generator = StudentGenerator(self.db, self.config)
        self.score_generator = ScoreGenerator(self.db, self.config)
        self.attendance_generator = AttendanceGenerator(self.db, self.config)

    def generate_all(self, include_rules: bool = True) -> Dict[str, Any]:
        """
        生成完整的测试数据

        Args:
            include_rules: 是否同时生成预警规则

        Returns:
            生成统计信息
        """
        print("[*] 开始生成模拟数据...")
        start_time = datetime.now()

        results = {
            "success": False,
            "departments": 0,
            "classes": 0,
            "students": 0,
            "courses": 0,
            "scores": 0,
            "attendance_records": 0,
            "rules": 0,
            "errors": []
        }

        try:
            # 1. 生成基础数据（学院、班级、学生）
            print("  [1] 生成学院、班级和学生...")
            student_stats = self.student_generator.generate_all()
            results["departments"] = student_stats["departments"]
            results["classes"] = student_stats["classes"]
            results["students"] = student_stats["students"]

            # 2. 生成课程
            print("  [2] 生成课程...")
            courses = self.score_generator.generate_courses()
            results["courses"] = len(courses)

            # 3. 获取所有学生
            from app.models.student import Student
            students = self.db.query(Student).all()

            # 4. 生成成绩（两个学期）
            print("  [3] 生成成绩数据...")
            for semester in range(1, self.config.total_semesters + 1):
                score_stats = self.score_generator.generate_scores(
                    students, courses, semester
                )
                results["scores"] += score_stats["total_scores"]
                print(f"      学期{semester}: 平均分 {score_stats['average_score']}, "
                      f"及格率 {round(score_stats['pass_count']/max(1, score_stats['total_scores'])*100, 1)}%")

            # 5. 生成考勤
            print("  [4] 生成考勤数据...")
            attendance_stats = self.attendance_generator.generate_attendance(
                students, courses
            )
            results["attendance_records"] = attendance_stats["total_records"]
            print(f"      考勤记录: {attendance_stats['total_records']}条, "
                  f"缺勤率: {round(attendance_stats['absence_rate']*100, 2)}%")

            # 6. 生成连续缺勤案例
            print("  [5] 生成连续缺勤案例...")
            continuous_cases = self.attendance_generator.generate_continuous_absence_cases(
                students, courses, target_count=5
            )
            print(f"      生成连续缺勤案例: {continuous_cases}条记录")

            # 7. 生成预警规则
            if include_rules:
                print("  [6] 生成预警规则...")
                rules = self.generate_default_rules()
                results["rules"] = len(rules)

            # 8. 生成管理员用户
            print("  [7] 生成用户账号...")
            self.generate_default_users()

            self.db.commit()
            results["success"] = True

        except Exception as e:
            results["errors"].append(str(e))
            self.db.rollback()
            print(f"  [ERROR] 生成失败: {e}")

        end_time = datetime.now()
        results["duration"] = str(end_time - start_time)

        if results["success"]:
            print(f"\n[OK] 数据生成完成! 耗时: {results['duration']}")
            self._print_summary(results)

        return results

    def generate_default_rules(self) -> List[Any]:
        """生成默认预警规则"""
        from app.models.rule import Rule, RuleType, AlertLevel

        rules = [
            # 成绩预警规则
            Rule(
                code="SCORE_FAIL_1",
                name="单科成绩不及格",
                type=RuleType.SCORE,
                level=AlertLevel.WARNING,
                conditions={
                    "metric": "score",
                    "operator": "<",
                    "threshold": 60
                },
                description="单科成绩低于60分",
                is_active=True
            ),
            Rule(
                code="SCORE_FAIL_3",
                name="多门课程挂科",
                type=RuleType.SCORE,
                level=AlertLevel.SERIOUS,
                conditions={
                    "metric": "fail_count",
                    "operator": ">=",
                    "threshold": 3,
                    "time_window": "1学期"
                },
                description="一学期内挂科3门及以上",
                is_active=True
            ),
            Rule(
                code="SCORE_AVG_LOW",
                name="平均成绩过低",
                type=RuleType.SCORE,
                level=AlertLevel.WARNING,
                conditions={
                    "metric": "score",
                    "operator": "<",
                    "threshold": 65,
                    "aggregation": "avg"
                },
                description="平均成绩低于65分",
                is_active=True
            ),
            Rule(
                code="SCORE_GPA_LOW",
                name="GPA低于2.0",
                type=RuleType.SCORE,
                level=AlertLevel.SERIOUS,
                conditions={
                    "metric": "gpa",
                    "operator": "<",
                    "threshold": 2.0
                },
                description="GPA低于2.0",
                is_active=True
            ),

            # 考勤预警规则
            Rule(
                code="ATTEND_ABSENT_1",
                name="单次缺勤",
                type=RuleType.ATTENDANCE,
                level=AlertLevel.WARNING,
                conditions={
                    "metric": "absence_count",
                    "operator": ">=",
                    "threshold": 1,
                    "time_window": "1周"
                },
                description="一周内缺勤1次及以上",
                is_active=True
            ),
            Rule(
                code="ATTEND_CONT_3",
                name="连续缺勤3次",
                type=RuleType.ATTENDANCE,
                level=AlertLevel.SERIOUS,
                conditions={
                    "metric": "continuous_absence",
                    "operator": ">=",
                    "threshold": 3
                },
                description="连续缺勤3次及以上",
                is_active=True
            ),
            Rule(
                code="ATTEND_RATE_HIGH",
                name="缺勤率过高",
                type=RuleType.ATTENDANCE,
                level=AlertLevel.URGENT,
                conditions={
                    "metric": "absence_rate",
                    "operator": ">=",
                    "threshold": 0.15,
                    "time_window": "1个月"
                },
                description="月缺勤率达到15%及以上",
                is_active=True
            ),

            # 综合预警规则
            Rule(
                code="COMPREHENSIVE_RISK",
                name="学业综合风险",
                type=RuleType.GRADUATION,
                level=AlertLevel.URGENT,
                conditions={
                    "metric": "fail_count",
                    "operator": ">=",
                    "threshold": 2,
                    "time_window": "1学期"
                },
                description="一学期挂科2门以上且缺勤率超过10%",
                is_active=True
            ),
        ]

        for rule in rules:
            self.db.add(rule)

        self.db.flush()
        return rules

    def generate_default_users(self) -> List[Any]:
        """生成默认用户账号"""
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash

        users = [
            User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                is_active=True,
                first_login=False  # 测试账号无需修改密码
            ),
            User(
                username="counselor",
                password_hash=get_password_hash("counselor123"),
                role=UserRole.COUNSELOR,
                is_active=True,
                first_login=False  # 测试账号无需修改密码
            ),
        ]

        for user in users:
            # 检查是否已存在
            existing = self.db.query(User).filter(
                User.username == user.username
            ).first()
            if not existing:
                self.db.add(user)

        self.db.flush()
        return users

    def _print_summary(self, results: Dict[str, Any]):
        """打印生成结果摘要"""
        print("\n" + "=" * 50)
        print("[摘要] 数据生成摘要")
        print("=" * 50)
        print(f"  学院数量: {results['departments']}")
        print(f"  班级数量: {results['classes']}")
        print(f"  学生数量: {results['students']}")
        print(f"  课程数量: {results['courses']}")
        print(f"  成绩记录: {results['scores']}")
        print(f"  考勤记录: {results['attendance_records']}")
        print(f"  预警规则: {results['rules']}")
        print("=" * 50)

    def clear_all(self) -> Dict[str, int]:
        """
        清空所有模拟数据

        Returns:
            删除统计
        """
        from app.models.alert import Alert, AlertRecord
        from app.models.attendance import Attendance
        from app.models.score import Score
        from app.models.course import Course
        from app.models.student import Student, Class, Department
        from app.models.rule import Rule
        from app.models.user import User

        stats = {
            "alerts": 0,
            "alert_records": 0,
            "attendance": 0,
            "scores": 0,
            "courses": 0,
            "students": 0,
            "classes": 0,
            "departments": 0,
            "rules": 0,
            "users": 0
        }

        try:
            # 按依赖顺序删除
            stats["alert_records"] = self.db.query(AlertRecord).delete()
            stats["alerts"] = self.db.query(Alert).delete()
            stats["attendance"] = self.db.query(Attendance).delete()
            stats["scores"] = self.db.query(Score).delete()
            stats["courses"] = self.db.query(Course).delete()
            stats["students"] = self.db.query(Student).delete()
            stats["classes"] = self.db.query(Class).delete()
            stats["departments"] = self.db.query(Department).delete()
            stats["rules"] = self.db.query(Rule).delete()
            # 保留管理员账号
            # stats["users"] = self.db.query(User).delete()

            self.db.commit()
            print("[OK] 数据已清空")

        except Exception as e:
            self.db.rollback()
            print(f"[ERROR] 清空失败: {e}")

        return stats

    def get_statistics(self) -> Dict[str, Any]:
        """获取当前数据库统计信息"""
        from app.models.alert import Alert
        from app.models.attendance import Attendance
        from app.models.score import Score
        from app.models.course import Course
        from app.models.student import Student, Class, Department
        from app.models.rule import Rule

        stats = {
            "departments": self.db.query(Department).count(),
            "classes": self.db.query(Class).count(),
            "students": self.db.query(Student).count(),
            "courses": self.db.query(Course).count(),
            "scores": self.db.query(Score).count(),
            "attendance": self.db.query(Attendance).count(),
            "rules": self.db.query(Rule).count(),
            "alerts": self.db.query(Alert).count(),
        }

        return stats


def create_simulator(db: Session, config: Optional[SimulationConfig] = None) -> DataSimulator:
    """
    创建数据模拟器实例

    Args:
        db: 数据库会话
        config: 模拟配置

    Returns:
        数据模拟器实例
    """
    return DataSimulator(db, config)
