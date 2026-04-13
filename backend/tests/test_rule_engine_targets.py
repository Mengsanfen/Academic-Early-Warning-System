from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.database import Base
from app.core.rule_engine.simple_engine import SimpleRuleEngine
from app.models.alert import Alert
from app.models.course import Course, CourseType
from app.models.rule import AlertLevel, Rule, RuleType, TargetType
from app.models.score import Score
from app.models.student import Class, Department, Student, StudentStatus


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_rule_engine_applies_grade_scope_and_required_credit_metric(db_session):
    department = Department(name="计算机学院", code="CS")
    db_session.add(department)
    db_session.flush()

    class_2024 = Class(name="软件工程1班", grade="2024", department_id=department.id)
    class_2023 = Class(name="软件工程2班", grade="2023", department_id=department.id)
    db_session.add_all([class_2024, class_2023])
    db_session.flush()

    target_student = Student(
        student_no="20240001",
        name="张三",
        gender="male",
        class_id=class_2024.id,
        status=StudentStatus.ACTIVE,
        is_active=True,
    )
    other_student = Student(
        student_no="20230001",
        name="李四",
        gender="female",
        class_id=class_2023.id,
        status=StudentStatus.ACTIVE,
        is_active=True,
    )
    db_session.add_all([target_student, other_student])
    db_session.flush()

    required_course = Course(
        course_code="REQ101",
        course_name="高等数学",
        credit=3,
        semester="2024-2025-1",
        class_id=class_2024.id,
        course_type=CourseType.REQUIRED,
    )
    elective_course = Course(
        course_code="ELC101",
        course_name="艺术鉴赏",
        credit=2,
        semester="2024-2025-1",
        class_id=class_2024.id,
        course_type=CourseType.ELECTIVE,
    )
    other_course = Course(
        course_code="REQ201",
        course_name="大学英语",
        credit=4,
        semester="2024-2025-1",
        class_id=class_2023.id,
        course_type=CourseType.REQUIRED,
    )
    db_session.add_all([required_course, elective_course, other_course])
    db_session.flush()

    db_session.add_all(
        [
            Score(
                student_id=target_student.id,
                course_id=required_course.id,
                score=82,
                semester="2024-2025-1",
                exam_type="期末",
            ),
            Score(
                student_id=target_student.id,
                course_id=elective_course.id,
                score=95,
                semester="2024-2025-1",
                exam_type="期末",
            ),
            Score(
                student_id=other_student.id,
                course_id=other_course.id,
                score=88,
                semester="2024-2025-1",
                exam_type="期末",
            ),
        ]
    )

    rule = Rule(
        name="2024级必修学分不足",
        code="REQ_CREDIT_2024",
        type=RuleType.GRADUATION,
        level=AlertLevel.SERIOUS,
        is_active=True,
        target_type=TargetType.GRADES,
        target_grades=["2024"],
        conditions={
            "metric": "earned_credit",
            "operator": "<",
            "threshold": 4,
            "course_type": "required",
        },
        message_template="学生{student_name}必修学分不足，当前 {metric_value}",
    )
    db_session.add(rule)
    db_session.commit()

    engine = SimpleRuleEngine(db_session)
    result = engine.execute_all_rules()

    alerts = db_session.query(Alert).filter(Alert.rule_id == rule.id).all()

    assert result["alerts_created"] == 1
    assert len(alerts) == 1
    assert alerts[0].student_id == target_student.id
