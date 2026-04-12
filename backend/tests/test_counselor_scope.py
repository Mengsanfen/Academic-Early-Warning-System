import asyncio
import io
import sys
from pathlib import Path

import openpyxl
import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.api.v1 import dashboard_secure, import_export
from app.api.v1 import students as students_api
from app.database import Base
from app.models.alert import Alert, AlertStatus
from app.models.attendance import Attendance
from app.models.course import Course
from app.models.rule import AlertLevel, Rule, RuleType
from app.models.score import Score
from app.models.student import Class, Department, Student, StudentStatus
from app.models.user import User, UserRole


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


def _build_workbook(headers, rows):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def _seed_scope_data(db):
    department = Department(name="计算机学院", code="CS")
    db.add(department)
    db.flush()

    class_a = Class(name="软件工程1班", grade="2024", department_id=department.id)
    class_b = Class(name="软件工程2班", grade="2024", department_id=department.id)
    db.add_all([class_a, class_b])
    db.flush()

    counselor = User(
        username="counselor_a",
        password_hash="hash",
        role=UserRole.COUNSELOR,
        managed_class_ids=str(class_a.id),
        is_active=True,
    )
    admin = User(
        username="admin",
        password_hash="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add_all([counselor, admin])
    db.flush()

    student_a = Student(
        student_no="20240001",
        name="张三",
        gender="male",
        class_id=class_a.id,
        phone="13800000001",
        email="zhangsan@example.com",
        status=StudentStatus.ACTIVE,
        is_active=True,
    )
    student_b = Student(
        student_no="20240002",
        name="李四",
        gender="female",
        class_id=class_b.id,
        phone="13800000002",
        email="lisi@example.com",
        status=StudentStatus.ACTIVE,
        is_active=True,
    )
    db.add_all([student_a, student_b])
    db.flush()

    score_rule = Rule(
        name="成绩预警",
        code="SCORE_WARN",
        type=RuleType.SCORE,
        conditions={},
        level=AlertLevel.WARNING,
        is_active=True,
    )
    db.add(score_rule)
    db.flush()

    alert_a = Alert(
        student_id=student_a.id,
        rule_id=score_rule.id,
        level=AlertLevel.WARNING,
        message="张三成绩预警",
        status=AlertStatus.PENDING,
    )
    alert_b = Alert(
        student_id=student_b.id,
        rule_id=score_rule.id,
        level=AlertLevel.SERIOUS,
        message="李四成绩预警",
        status=AlertStatus.PROCESSING,
    )
    db.add_all([alert_a, alert_b])
    db.commit()

    return {
        "department": department,
        "class_a": class_a,
        "class_b": class_b,
        "counselor": counselor,
        "admin": admin,
        "student_a": student_a,
        "student_b": student_b,
        "rule": score_rule,
    }


def test_counselor_student_list_is_scoped(db_session):
    data = _seed_scope_data(db_session)

    result = students_api.get_students(
        page=1,
        page_size=20,
        db=db_session,
        current_user=data["counselor"],
    )

    assert result["total"] == 1
    assert [item["student_no"] for item in result["items"]] == ["20240001"]


def test_counselor_dashboard_overview_is_scoped(db_session):
    data = _seed_scope_data(db_session)

    result = dashboard_secure.get_overview(
        db=db_session,
        current_user=data["counselor"],
    )

    assert result["student_count"] == 1
    assert result["alert_count"]["total"] == 1
    assert result["alert_count"]["pending"] == 1
    assert result["alert_count"]["processing"] == 0
    assert [item["student_no"] for item in result["recent_alerts"]] == ["20240001"]


def test_counselor_create_student_rejects_other_class(db_session):
    data = _seed_scope_data(db_session)

    with pytest.raises(HTTPException) as exc_info:
        students_api.create_student(
            data=students_api.StudentCreate(
                student_no="20240003",
                name="王五",
                gender="male",
                class_id=data["class_b"].id,
                grade=2024,
            ),
            db=db_session,
            current_user=data["counselor"],
        )

    assert exc_info.value.status_code == 403


def test_counselor_score_import_rejects_other_class_rows(db_session):
    data = _seed_scope_data(db_session)
    workbook = _build_workbook(
        ["学号", "课程代码", "课程名称", "成绩", "学分", "学期", "考试类型"],
        [
            ["20240001", "CS101A", "高等数学", 85, 4, "2024-2025-1", "期末"],
            ["20240002", "CS101B", "线性代数", 78, 4, "2024-2025-1", "期末"],
        ],
    )
    upload = UploadFile(filename="scores.xlsx", file=workbook)

    result = asyncio.run(
        import_export.import_scores(
            file=upload,
            update_existing=False,
            db=db_session,
            current_user=data["counselor"],
        )
    )

    saved_scores = db_session.query(Score).all()
    saved_courses = db_session.query(Course).order_by(Course.course_code.asc()).all()

    assert result.total == 2
    assert result.success == 1
    assert result.failed == 1
    assert len(saved_scores) == 1
    assert saved_scores[0].student_id == data["student_a"].id
    assert [course.course_code for course in saved_courses] == ["CS101A"]
    assert any("无权导入该学生所在班级的数据" in error for error in result.errors)


def test_counselor_attendance_import_rejects_other_class_rows(db_session):
    data = _seed_scope_data(db_session)
    workbook = _build_workbook(
        ["学号", "课程代码", "课程名称", "日期", "状态", "备注"],
        [
            ["20240001", "CS201A", "数据结构", "2026-03-01", "正常", ""],
            ["20240002", "CS201B", "操作系统", "2026-03-01", "缺勤", "跨班数据"],
        ],
    )
    upload = UploadFile(filename="attendances.xlsx", file=workbook)

    result = asyncio.run(
        import_export.import_attendances(
            file=upload,
            db=db_session,
            current_user=data["counselor"],
        )
    )

    saved_courses = db_session.query(Course).order_by(Course.course_code.asc()).all()
    attendance_count = db_session.query(Attendance).count()

    assert result.total == 2
    assert result.success == 1
    assert result.failed == 1
    assert attendance_count == 1
    assert [course.course_code for course in saved_courses] == ["CS201A"]
    assert any("无权导入该学生所在班级的数据" in error for error in result.errors)
