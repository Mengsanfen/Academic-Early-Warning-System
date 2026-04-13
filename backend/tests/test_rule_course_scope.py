import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.v1 import courses as courses_api
from app.api.v1 import rules_secure
from app.main import app
from app.core.rule_engine.simple_engine import SimpleRuleEngine
from app.database import Base
from app.models.course import Course, CourseType
from app.models.score import Score
from app.models.rule import AlertLevel, RuleType, TargetType
from app.models.student import Class, Department, Student, StudentStatus
from app.models.user import User, UserRole


@pytest.fixture()
def db_session():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
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


def seed_basic_data(db):
    department = Department(name='计算机学院', code='CS')
    db.add(department)
    db.flush()

    class_a = Class(name='2024级软件1班', grade='2024', department_id=department.id)
    class_b = Class(name='2023级软件2班', grade='2023', department_id=department.id)
    db.add_all([class_a, class_b])
    db.flush()

    admin = User(username='admin', password_hash='hash', role=UserRole.ADMIN, is_active=True)
    counselor = User(
        username='counselor',
        password_hash='hash',
        role=UserRole.COUNSELOR,
        managed_class_ids=str(class_a.id),
        is_active=True,
    )
    db.add_all([admin, counselor])
    db.flush()

    student = Student(
        student_no='20240001',
        name='张三',
        gender='male',
        class_id=class_a.id,
        phone='13800000000',
        email='zhangsan@example.com',
        status=StudentStatus.ACTIVE,
        is_active=True,
    )
    db.add(student)
    db.flush()

    return {
        'department': department,
        'class_a': class_a,
        'class_b': class_b,
        'admin': admin,
        'counselor': counselor,
        'student': student,
    }


def test_create_rule_rejects_empty_grade_scope(db_session):
    data = seed_basic_data(db_session)

    with pytest.raises(HTTPException) as exc_info:
        rules_secure.create_rule(
            data=rules_secure.RuleCreate(
                name='按年级测试规则',
                code='GRADE_SCOPE_RULE',
                type=RuleType.SCORE,
                conditions={'metric': 'score', 'operator': '<', 'threshold': 60},
                level=AlertLevel.WARNING,
                target_type=TargetType.GRADES,
                target_grades=[],
            ),
            db=db_session,
            _=data['admin'],
        )

    assert exc_info.value.status_code == 400


def test_create_rule_supports_course_type_and_grade_scope(db_session):
    data = seed_basic_data(db_session)

    rule = rules_secure.create_rule(
        data=rules_secure.RuleCreate(
            name='必修学分不足',
            code='REQUIRED_CREDIT_SHORTAGE',
            type=RuleType.GRADUATION,
            conditions={
                'metric': 'earned_credit',
                'operator': '<',
                'threshold': 30,
                'course_type': 'required',
            },
            level=AlertLevel.SERIOUS,
            target_type=TargetType.GRADES,
            target_grades=['2024'],
        ),
        db=db_session,
        _=data['admin'],
    )

    assert rule.target_type == TargetType.GRADES
    assert rule.target_grades == ['2024']
    assert rule.conditions['course_type'] == 'required'


def test_get_semesters_is_scoped_for_counselor(db_session):
    data = seed_basic_data(db_session)
    db_session.add_all([
        Course(course_code='CS101', course_name='高等数学', credit=4, semester='2024-2025-1', class_id=data['class_a'].id, course_type=CourseType.REQUIRED),
        Course(course_code='CS201', course_name='操作系统', credit=3, semester='2023-2024-2', class_id=data['class_b'].id, course_type=CourseType.REQUIRED),
    ])
    db_session.commit()

    result = courses_api.get_semesters(db=db_session, current_user=data['counselor'])

    assert result['items'] == ['2024-2025-1']


def test_get_course_blocks_unmanaged_class_for_counselor(db_session):
    data = seed_basic_data(db_session)
    course = Course(
        course_code='CS301',
        course_name='数据库系统',
        credit=3,
        semester='2023-2024-2',
        class_id=data['class_b'].id,
        course_type=CourseType.REQUIRED,
    )
    db_session.add(course)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        courses_api.get_course(course_id=course.id, db=db_session, current_user=data['counselor'])

    assert exc_info.value.status_code == 403


def test_credit_metric_distinguishes_required_and_elective(db_session):
    data = seed_basic_data(db_session)
    required_course = Course(
        course_code='CS401',
        course_name='编译原理',
        credit=3,
        semester='2024-2025-1',
        class_id=data['class_a'].id,
        course_type=CourseType.REQUIRED,
    )
    elective_course = Course(
        course_code='EL101',
        course_name='创新创业',
        credit=2,
        semester='2024-2025-1',
        class_id=data['class_a'].id,
        course_type=CourseType.ELECTIVE,
    )
    db_session.add_all([required_course, elective_course])
    db_session.flush()

    db_session.add_all([
        Score(student_id=data['student'].id, course_id=required_course.id, score=88, semester='2024-2025-1', exam_type='期末'),
        Score(student_id=data['student'].id, course_id=elective_course.id, score=75, semester='2024-2025-1', exam_type='期末'),
    ])
    db_session.commit()

    engine = SimpleRuleEngine(db_session)

    assert engine._calculate_metric(data['student'].id, 'earned_credit', None, 'required') == 3
    assert engine._calculate_metric(data['student'].id, 'earned_credit', None, 'elective') == 2
    assert engine._calculate_metric(data['student'].id, 'earned_credit', None, None) == 5


def test_lowercase_rule_target_type_can_be_loaded(db_session):
    data = seed_basic_data(db_session)
    db_session.execute(
        text(
            """
            INSERT INTO rules (
                name, code, type, conditions, level, is_active, target_type, id, created_at, updated_at
            )
            VALUES (
                :name, :code, :type, :conditions, :level, :is_active, :target_type, :id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "name": "范围测试",
            "code": "TARGET_SCOPE_ENUM",
            "type": "SCORE",
            "conditions": "{}",
            "level": "WARNING",
            "is_active": 1,
            "target_type": "all",
            "id": 9991,
        },
    )
    db_session.commit()

    overview = rules_secure.get_rules(page=1, page_size=20, db=db_session, _=data["admin"])

    assert any(item.target_type == TargetType.ALL for item in overview["items"])


def test_lowercase_course_type_can_be_loaded(db_session):
    data = seed_basic_data(db_session)
    db_session.execute(
        text(
            """
            INSERT INTO courses (
                course_code, course_name, credit, semester, class_id, teacher_name, course_type, id, created_at, updated_at
            )
            VALUES (
                :course_code, :course_name, :credit, :semester, :class_id, :teacher_name, :course_type, :id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "course_code": "ENUM101",
            "course_name": "枚举兼容测试",
            "credit": 2,
            "semester": "2024-2025-1",
            "class_id": data["class_a"].id,
            "teacher_name": "测试教师",
            "course_type": "required",
            "id": 9992,
        },
    )
    db_session.commit()

    result = courses_api.get_courses(page=1, page_size=20, db=db_session, current_user=data["admin"])

    assert any(item["course_code"] == "ENUM101" and item["course_type"] == "required" for item in result["items"])


def test_static_rule_routes_precede_dynamic_rule_detail_route():
    route_paths = [getattr(route, "path", "") for route in app.routes]

    assert route_paths.index("/api/v1/rules/templates") < route_paths.index("/api/v1/rules/{rule_id}")
    assert route_paths.index("/api/v1/rules/grades") < route_paths.index("/api/v1/rules/{rule_id}")
    assert route_paths.index("/api/v1/rules/target-options") < route_paths.index("/api/v1/rules/{rule_id}")
