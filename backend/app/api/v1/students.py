"""
学生管理 API

包含基于用户角色的数据权限过滤
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from app.database import get_db
from app.api.deps import (
    get_current_user,
    get_counselor_or_admin,
    apply_class_filter,
    check_student_access,
    get_accessible_class_ids
)
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.student import Class


logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Schemas ==========

class StudentCreate(BaseModel):
    """创建学生"""
    student_no: str
    name: str
    gender: str = "男"
    class_id: int
    grade: int
    phone: Optional[str] = None
    email: Optional[str] = None
    id_card: Optional[str] = None
    address: Optional[str] = None


class StudentUpdate(BaseModel):
    """更新学生"""
    name: Optional[str] = None
    gender: Optional[str] = None
    class_id: Optional[int] = None
    grade: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    id_card: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class StudentResponse(BaseModel):
    """学生响应"""
    id: int
    student_no: str
    name: str
    gender: str
    class_id: int
    class_name: Optional[str] = None
    grade: int
    phone: Optional[str]
    email: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ========== API 端点 ==========

# ========== 学生端专用接口（必须在 /{student_id} 之前定义）==========

@router.get("/me/stats", summary="获取当前学生统计数据")
def get_my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录学生的统计数据

    仅限学生角色调用
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限学生访问"
        )

    if not current_user.student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到学生信息"
        )

    student_id = current_user.student.id

    # 导入模型
    from app.models.score import Score
    from app.models.attendance import Attendance, AttendanceStatus
    from app.models.alert import Alert
    from app.models.course import Course

    # 计算平均绩点（GPA）
    def score_to_grade_point(score: float) -> float:
        """成绩转绩点"""
        if score >= 90:
            return 4.0
        elif score >= 85:
            return 3.7
        elif score >= 82:
            return 3.3
        elif score >= 78:
            return 3.0
        elif score >= 75:
            return 2.7
        elif score >= 72:
            return 2.3
        elif score >= 68:
            return 2.0
        elif score >= 64:
            return 1.5
        elif score >= 60:
            return 1.0
        else:
            return 0.0

    scores = db.query(Score).join(Course).filter(Score.student_id == student_id).all()
    avg_gpa = 0
    if scores:
        # 计算加权平均绩点（学分 * 绩点）/ 总学分
        total_credits = 0
        total_grade_points = 0
        for s in scores:
            if s.course:
                credit = float(s.course.credit)
                gp = score_to_grade_point(float(s.score))
                total_credits += credit
                total_grade_points += credit * gp
        if total_credits > 0:
            avg_gpa = round(total_grade_points / total_credits, 2)

    # 计算出勤率
    attendances = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    attendance_rate = 0
    if attendances:
        present_count = sum(1 for a in attendances if a.status == AttendanceStatus.PRESENT)
        attendance_rate = round(present_count / len(attendances) * 100, 1)

    # 预警数量
    alert_count = db.query(Alert).filter(Alert.student_id == student_id).count()

    # 已获学分（及格课程的学分）
    passed_scores = db.query(Score).join(Course).filter(
        Score.student_id == student_id,
        Score.score >= 60
    ).all()
    earned_credits = sum(float(s.course.credit) for s in passed_scores if s.course)

    return {
        "avgScore": avg_gpa,
        "attendanceRate": attendance_rate,
        "alertCount": alert_count,
        "earnedCredits": round(earned_credits, 1)
    }


@router.get("/me/grades", summary="获取当前学生成绩列表")
def get_my_grades(
    semester: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录学生的成绩列表

    仅限学生角色调用
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限学生访问"
        )

    if not current_user.student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到学生信息"
        )

    student_id = current_user.student.id

    from app.models.score import Score
    from app.models.course import Course

    query = db.query(Score).join(Course).filter(Score.student_id == student_id)

    if semester:
        query = query.filter(Score.semester == semester)

    # 状态过滤
    if status == "pass":
        query = query.filter(Score.score >= 60)
    elif status == "fail":
        query = query.filter(Score.score < 60)

    scores = query.order_by(Score.semester.desc(), Score.id.desc()).all()

    items = []
    for s in scores:
        # 计算绩点
        score_val = float(s.score)
        if score_val >= 90:
            grade_point = 4.0
        elif score_val >= 85:
            grade_point = 3.7
        elif score_val >= 82:
            grade_point = 3.3
        elif score_val >= 78:
            grade_point = 3.0
        elif score_val >= 75:
            grade_point = 2.7
        elif score_val >= 72:
            grade_point = 2.3
        elif score_val >= 68:
            grade_point = 2.0
        elif score_val >= 64:
            grade_point = 1.5
        elif score_val >= 60:
            grade_point = 1.0
        else:
            grade_point = 0.0

        items.append({
            "id": s.id,
            "course_name": s.course.course_name if s.course else None,
            "course_code": s.course.course_code if s.course else None,
            "credit": float(s.course.credit) if s.course else 0,
            "semester": s.semester,
            "score": score_val,
            "grade_point": grade_point
        })

    return {
        "items": items,
        "total": len(items)
    }


@router.get("/me/attendance", summary="获取当前学生考勤记录")
def get_my_attendance(
    page: int = 1,
    page_size: int = 20,
    course: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录学生的考勤记录

    仅限学生角色调用
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限学生访问"
        )

    if not current_user.student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到学生信息"
        )

    student_id = current_user.student.id

    from app.models.attendance import Attendance, AttendanceStatus
    from app.models.course import Course
    from datetime import datetime as dt

    query = db.query(Attendance).join(Course, isouter=True).filter(
        Attendance.student_id == student_id
    )

    # 课程过滤
    if course:
        query = query.filter(Course.course_name.like(f"%{course}%"))

    # 状态过滤
    if status:
        try:
            status_enum = AttendanceStatus(status)
            query = query.filter(Attendance.status == status_enum)
        except ValueError:
            pass

    # 日期过滤
    if start_date:
        try:
            start = dt.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date >= start)
        except ValueError:
            pass

    if end_date:
        try:
            end = dt.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date <= end)
        except ValueError:
            pass

    # 统计
    total = query.count()

    # 分页
    attendances = query.order_by(Attendance.date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # 计算统计数据
    all_attendances = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).all()

    stats = {
        "normal": sum(1 for a in all_attendances if a.status == AttendanceStatus.PRESENT),
        "late": sum(1 for a in all_attendances if a.status == AttendanceStatus.LATE),
        "absent": sum(1 for a in all_attendances if a.status == AttendanceStatus.ABSENT),
        "leave": sum(1 for a in all_attendances if a.status == AttendanceStatus.LEAVE)
    }

    items = []
    for a in attendances:
        items.append({
            "id": a.id,
            "course_name": a.course.course_name if a.course else None,
            "date": a.date.isoformat() if a.date else None,
            "week": None,  # 暂无周次信息
            "time": None,  # 暂无时间信息
            "status": a.status.value if a.status else None,
            "remark": a.remark
        })

    return {
        "items": items,
        "total": total,
        "stats": stats
    }


@router.get("/me/alerts", summary="获取当前学生预警列表")
def get_my_alerts(
    page: int = 1,
    page_size: int = 20,
    type: Optional[str] = None,
    level: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录学生的预警列表

    仅限学生角色调用
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限学生访问"
        )

    if not current_user.student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到学生信息"
        )

    student_id = current_user.student.id

    from app.models.alert import Alert, AlertStatus
    from app.models.rule import AlertLevel, RuleType

    query = db.query(Alert).filter(Alert.student_id == student_id)

    # 类型过滤（前端传 grade/attendance/credit/comprehensive，后端是 score/attendance/graduation）
    if type:
        type_mapping = {
            "grade": RuleType.SCORE,
            "attendance": RuleType.ATTENDANCE,
            "credit": RuleType.GRADUATION,
            "comprehensive": None
        }
        if type in type_mapping and type_mapping[type]:
            query = query.join(Alert.rule).filter(Alert.rule.property('type') == type_mapping[type])

    # 级别过滤（前端传 high/medium/low，后端是 urgent/serious/warning）
    if level:
        level_mapping = {
            "high": AlertLevel.URGENT,
            "medium": AlertLevel.SERIOUS,
            "low": AlertLevel.WARNING
        }
        if level in level_mapping:
            query = query.filter(Alert.level == level_mapping[level])

    # 状态过滤
    if status_filter:
        try:
            status_enum = AlertStatus(status_filter)
            query = query.filter(Alert.status == status_enum)
        except ValueError:
            pass

    # 统计
    total = query.count()

    # 分页
    alerts = query.order_by(Alert.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # 计算统计数据（映射到前端期望的格式）
    all_alerts = db.query(Alert).filter(Alert.student_id == student_id).all()

    stats = {
        "total": len(all_alerts),
        "high": sum(1 for a in all_alerts if a.level == AlertLevel.URGENT),
        "medium": sum(1 for a in all_alerts if a.level == AlertLevel.SERIOUS),
        "low": sum(1 for a in all_alerts if a.level == AlertLevel.WARNING)
    }

    items = []
    for a in alerts:
        # 从rule获取alert_type，映射到前端格式
        alert_type = "comprehensive"
        if a.rule and a.rule.type:
            type_mapping_reverse = {
                RuleType.SCORE: "grade",
                RuleType.ATTENDANCE: "attendance",
                RuleType.GRADUATION: "credit"
            }
            alert_type = type_mapping_reverse.get(a.rule.type, "comprehensive")

        # 级别映射到前端格式
        level_mapping_reverse = {
            AlertLevel.URGENT: "high",
            AlertLevel.SERIOUS: "medium",
            AlertLevel.WARNING: "low"
        }
        alert_level = level_mapping_reverse.get(a.level, "low") if a.level else None

        items.append({
            "id": a.id,
            "alert_type": alert_type,
            "alert_level": alert_level,
            "description": a.message,
            "suggestion": None,  # 暂无建议字段
            "status": a.status.value if a.status else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None
        })

    return {
        "items": items,
        "total": total,
        "stats": stats
    }


# ========== 通用接口 ==========

@router.get("/list/classes", summary="获取班级列表", response_model=List[dict])
def get_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """
    获取当前用户可访问的班级列表

    返回:
    - admin: 所有班级
    - counselor: 其管理的班级
    - student: 自己所在的班级
    """
    class_ids = get_accessible_class_ids(current_user)

    if class_ids == []:
        # 无权限，返回空数组
        return []

    query = db.query(Class)

    if class_ids is not None:
        # 有限制的班级ID列表
        query = query.filter(Class.id.in_(class_ids))
    # else: None 表示无限制（admin），查询所有

    classes = query.order_by(Class.id.desc()).all()

    return [
        {
            "id": c.id,
            "name": c.name,
            "grade": c.grade
        }
        for c in classes
    ]


@router.get("/accessible-classes", summary="获取可访问的班级列表")
def get_accessible_classes(
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户可访问的班级列表

    返回:
    - admin: 所有班级
    - counselor: 其管理的班级
    - student: 自己所在的班级
    """
    class_ids = get_accessible_class_ids(current_user)

    if class_ids == []:
        # 无权限
        return {"classes": []}

    query = db.query(Class).options(joinedload(Class.department))

    if class_ids is not None:
        # 有限制的班级ID列表
        query = query.filter(Class.id.in_(class_ids))

    if department_id:
        query = query.filter(Class.department_id == department_id)

    classes = query.all()

    return {
        "classes": [
            {
                "id": c.id,
                "name": c.name,
                "grade": c.grade,
                "department_id": c.department_id,
                "department_name": c.department.name if c.department else None,
                "student_count": len(c.students) if c.students else 0
            }
            for c in classes
        ]
    }


@router.get("", response_model=dict, summary="获取学生列表")
def get_students(
    page: int = 1,
    page_size: int = 20,
    class_id: Optional[int] = None,
    name: Optional[str] = None,
    student_no: Optional[str] = None,
    grade: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取学生列表

    权限控制：
    - admin: 可以查看所有学生
    - counselor: 只能查看其管理班级的学生
    - student: 只能查看自己的信息
    """
    # 基础查询
    query = db.query(Student).join(Class, isouter=True)

    # ========== 核心权限过滤 ==========
    # 根据用户角色应用班级过滤
    query = apply_class_filter(query, current_user, Student.class_id)

    # 如果是学生角色，只能查看自己
    if current_user.role == UserRole.STUDENT:
        if not current_user.student:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
        query = query.filter(Student.id == current_user.student.id)

    # ========== 业务过滤条件 ==========
    # 班级过滤（需要检查权限）
    if class_id:
        # 检查用户是否有权限访问该班级
        if current_user.role == UserRole.COUNSELOR:
            managed_ids = current_user.get_managed_class_ids()
            if class_id not in managed_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您没有权限访问该班级的学生"
                )
        query = query.filter(Student.class_id == class_id)

    if name:
        query = query.filter(Student.name.like(f"%{name}%"))

    if student_no:
        query = query.filter(Student.student_no.like(f"%{student_no}%"))

    if grade:
        query = query.filter(Class.grade == str(grade))

    if is_active is not None:
        query = query.filter(Student.is_active == is_active)

    # 统计和分页
    total = query.count()
    students = query.order_by(Student.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 构建响应
    items = []
    for s in students:
        items.append({
            "id": s.id,
            "student_no": s.student_no,
            "name": s.name,
            "gender": s.gender,
            "class_id": s.class_id,
            "class_name": s.class_info.name if s.class_info else None,
            "grade": s.class_info.grade if s.class_info else None,
            "phone": s.phone,
            "email": s.email,
            "is_active": s.is_active,
            "created_at": s.created_at
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{student_id:int}", response_model=dict, summary="获取学生详情")
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if student_id < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="学生ID必须大于0"
        )
    """
    获取学生详情

    权限控制：
    - admin: 可以查看所有学生
    - counselor: 只能查看其管理班级的学生
    - student: 只能查看自己的信息
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    # ========== 权限检查 ==========
    # 检查是否有权限访问该学生
    if not check_student_access(current_user, student_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限访问该学生的信息"
        )

    return {
        "id": student.id,
        "student_no": student.student_no,
        "name": student.name,
        "gender": student.gender,
        "class_id": student.class_id,
        "class_name": student.class_info.name if student.class_info else None,
        "grade": student.class_info.grade if student.class_info else None,
        "phone": student.phone,
        "email": student.email,
        "id_card": getattr(student, 'id_card', None),
        "address": getattr(student, 'address', None),
        "is_active": student.is_active,
        "created_at": student.created_at,
        "updated_at": student.updated_at
    }


@router.post("", response_model=StudentResponse, summary="创建学生")
def create_student(
    data: StudentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_counselor_or_admin)
):
    """
    创建学生（管理员和辅导员可操作）
    """
    # 检查学号是否已存在
    if db.query(Student).filter(Student.student_no == data.student_no).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号已存在"
        )

    # 检查班级是否存在
    class_info = db.query(Class).filter(Class.id == data.class_id).first()
    if not class_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="班级不存在"
        )

    student = Student(**data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)

    return StudentResponse.model_validate(student)


@router.put("/{student_id:int}", response_model=StudentResponse, summary="更新学生")
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin)
):
    """
    更新学生信息（管理员和辅导员可操作）

    辅导员只能更新其管理班级的学生
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    # ========== 权限检查 ==========
    # 辅导员只能修改其管理班级的学生
    if current_user.role == UserRole.COUNSELOR:
        if not check_student_access(current_user, student_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限修改该学生的信息"
            )

        # 如果要更改班级，检查是否有权限访问新班级
        if data.class_id:
            managed_ids = current_user.get_managed_class_ids()
            if data.class_id not in managed_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您没有权限将学生转移到该班级"
                )

    # 更新字段
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(student, key, value)

    db.commit()
    db.refresh(student)

    return StudentResponse.model_validate(student)


@router.delete("/{student_id:int}", summary="删除学生")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_counselor_or_admin)
):
    """
    删除学生（管理员和辅导员可操作）

    辅导员只能删除其管理班级的学生
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    # ========== 权限检查 ==========
    if current_user.role == UserRole.COUNSELOR:
        if not check_student_access(current_user, student_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限删除该学生"
            )

    db.delete(student)
    db.commit()

    return {"message": "删除成功"}


@router.get("/{student_id:int}/scores", summary="获取学生成绩")
def get_student_scores(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取学生成绩列表

    权限控制：
    - admin: 可以查看所有学生成绩
    - counselor: 只能查看其管理班级学生的成绩
    - student: 只能查看自己的成绩
    """
    # ========== 权限检查 ==========
    if not check_student_access(current_user, student_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限查看该学生的成绩"
        )

    from app.models.score import Score
    from app.models.course import Course

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    scores = db.query(Score).join(Course).filter(
        Score.student_id == student_id
    ).all()

    return {
        "student": {
            "id": student.id,
            "student_no": student.student_no,
            "name": student.name,
            "class_name": student.class_info.name if student.class_info else None
        },
        "scores": [
            {
                "id": s.id,
                "course_id": s.course_id,
                "course_name": s.course.course_name if s.course else None,
                "score": float(s.score) if s.score else None,
                "semester": s.semester,
                "exam_type": s.exam_type,
                "is_passed": s.is_passed
            }
            for s in scores
        ]
    }


@router.get("/{student_id:int}/attendances", summary="获取学生考勤")
def get_student_attendances(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取学生考勤记录

    权限控制：
    - admin: 可以查看所有学生考勤
    - counselor: 只能查看其管理班级学生的考勤
    - student: 只能查看自己的考勤
    """
    # ========== 权限检查 ==========
    if not check_student_access(current_user, student_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限查看该学生的考勤记录"
        )

    from app.models.attendance import Attendance, AttendanceStatus

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )

    attendances = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).order_by(Attendance.date.desc()).limit(50).all()

    return {
        "student": {
            "id": student.id,
            "student_no": student.student_no,
            "name": student.name,
            "class_name": student.class_info.name if student.class_info else None
        },
        "attendances": [
            {
                "id": a.id,
                "date": a.date.isoformat() if a.date else None,
                "status": a.status.value if a.status else None,
                "course_name": a.course.course_name if a.course else None,
                "remark": a.remark
            }
            for a in attendances
        ]
    }



