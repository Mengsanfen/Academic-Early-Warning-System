import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.rule_engine.simple_engine import SimpleRuleEngine
from app.database import Base
from app.models.alert import Alert, AlertStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.models.course import Course, CourseType
from app.models.rule import (
    AlertLevel,
    COMPREHENSIVE_RULE_CODE,
    Rule,
    RuleType,
    TargetType,
)
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


def seed_student_with_class(db_session):
    department = Department(name="计算机学院", code="CS")
    db_session.add(department)
    db_session.flush()

    clazz = Class(name="2024级软件1班", grade="2024", department_id=department.id)
    db_session.add(clazz)
    db_session.flush()

    student = Student(
        student_no="20240001",
        name="张三",
        gender="male",
        class_id=clazz.id,
        phone="13800000000",
        email="zhangsan@example.com",
        status=StudentStatus.ACTIVE,
        is_active=True,
    )
    db_session.add(student)
    db_session.flush()

    return clazz, student


def test_score_rule_reexecution_creates_and_resolves_alert_based_on_current_course_scores(db_session):
    clazz, student = seed_student_with_class(db_session)
    course_a = Course(
        course_code="MATH101",
        course_name="高等数学",
        credit=4,
        semester="2024-2025-1",
        class_id=clazz.id,
        course_type=CourseType.REQUIRED,
    )
    course_b = Course(
        course_code="ENG101",
        course_name="大学英语",
        credit=2,
        semester="2024-2025-1",
        class_id=clazz.id,
        course_type=CourseType.REQUIRED,
    )
    db_session.add_all([course_a, course_b])
    db_session.flush()

    score_a = Score(student_id=student.id, course_id=course_a.id, score=88, semester="2024-2025-1", exam_type="期末")
    score_b = Score(student_id=student.id, course_id=course_b.id, score=92, semester="2024-2025-1", exam_type="期末")
    db_session.add_all([score_a, score_b])
    db_session.add(
        Rule(
            name="单科不及格重跑测试",
            code="SCORE_FAIL_REEXECUTION",
            type=RuleType.SCORE,
            conditions={"metric": "score", "operator": "<", "threshold": 60},
            level=AlertLevel.WARNING,
            is_active=True,
            target_type=TargetType.ALL,
        )
    )
    db_session.commit()

    engine = SimpleRuleEngine(db_session)
    first_run = engine.execute_all_rules()
    assert first_run["alerts_created"] == 0

    score_a.score = 55
    db_session.commit()

    second_run = engine.execute_all_rules()
    assert second_run["alerts_created"] == 1

    alert = (
        db_session.query(Alert)
        .filter(Alert.student_id == student.id, Alert.status == AlertStatus.PENDING)
        .one()
    )
    assert alert.rule.code == "SCORE_FAIL_REEXECUTION"

    score_a.score = 68
    db_session.commit()

    third_run = engine.execute_all_rules()
    assert third_run["alerts_resolved"] == 1

    db_session.refresh(alert)
    assert alert.status == AlertStatus.RESOLVED


def test_rerunning_same_trigger_does_not_create_duplicate_active_alert(db_session):
    clazz, student = seed_student_with_class(db_session)
    course = Course(
        course_code="PHY101",
        course_name="大学物理",
        credit=3,
        semester="2024-2025-1",
        class_id=clazz.id,
        course_type=CourseType.REQUIRED,
    )
    db_session.add(course)
    db_session.flush()

    db_session.add(
        Score(student_id=student.id, course_id=course.id, score=50, semester="2024-2025-1", exam_type="期末")
    )
    db_session.add(
        Rule(
            name="挂科门数测试",
            code="FAIL_COUNT_REEXECUTION",
            type=RuleType.SCORE,
            conditions={"metric": "fail_count", "operator": ">=", "threshold": 1},
            level=AlertLevel.SERIOUS,
            is_active=True,
            target_type=TargetType.ALL,
        )
    )
    db_session.commit()

    engine = SimpleRuleEngine(db_session)
    first_run = engine.execute_all_rules()
    second_run = engine.execute_all_rules()

    assert first_run["alerts_created"] == 1
    assert second_run["alerts_created"] == 0
    active_count = (
        db_session.query(Alert)
        .filter(
            Alert.student_id == student.id,
            Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING]),
        )
        .count()
    )
    assert active_count == 1


def test_comprehensive_rule_reexecution_auto_resolves_after_recovery(db_session):
    clazz, student = seed_student_with_class(db_session)
    course_a = Course(
        course_code="CS201",
        course_name="数据结构",
        credit=3,
        semester="2024-2025-1",
        class_id=clazz.id,
        course_type=CourseType.REQUIRED,
    )
    course_b = Course(
        course_code="CS202",
        course_name="计算机组成原理",
        credit=3,
        semester="2024-2025-1",
        class_id=clazz.id,
        course_type=CourseType.REQUIRED,
    )
    db_session.add_all([course_a, course_b])
    db_session.flush()

    score_a = Score(student_id=student.id, course_id=course_a.id, score=50, semester="2024-2025-1", exam_type="期末")
    score_b = Score(student_id=student.id, course_id=course_b.id, score=58, semester="2024-2025-1", exam_type="期末")
    db_session.add_all([score_a, score_b])
    db_session.add_all(
        [
            Attendance(student_id=student.id, course_id=course_a.id, date=date(2025, 1, 5), status=AttendanceStatus.ABSENT),
            Attendance(student_id=student.id, course_id=course_a.id, date=date(2025, 1, 6), status=AttendanceStatus.ABSENT),
            Attendance(student_id=student.id, course_id=course_b.id, date=date(2025, 1, 7), status=AttendanceStatus.ABSENT),
        ]
    )
    db_session.commit()

    engine = SimpleRuleEngine(db_session)
    first_run = engine.execute_all_rules()
    assert first_run["alerts_created"] == 1

    alert = (
        db_session.query(Alert)
        .join(Alert.rule)
        .filter(Alert.student_id == student.id, Rule.code == COMPREHENSIVE_RULE_CODE)
        .one()
    )
    assert alert.status == AlertStatus.PENDING

    score_b.score = 65
    db_session.commit()

    second_run = engine.execute_all_rules()
    assert second_run["alerts_resolved"] == 1

    db_session.refresh(alert)
    assert alert.status == AlertStatus.RESOLVED
