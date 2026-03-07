import { request } from '@/utils/request'
import type { PageResponse, Student, Score, Attendance } from '@/types'

// 班级类型
export interface ClassInfo {
  id: number
  name: string
  grade?: string
  department_id?: number
  department_name?: string
  student_count?: number
}

// 院系类型
export interface Department {
  id: number
  name: string
  code?: string
  class_count?: number
}

// 获取班级列表
export function getClasses(departmentId?: number) {
  return request.get<{ items: ClassInfo[]; total: number }>('/classes', {
    params: { department_id: departmentId }
  })
}

// 获取院系列表
export function getDepartments() {
  return request.get<{ items: Department[]; total: number }>('/students/departments')
}

// 获取学生列表
export function getStudents(params: {
  page?: number
  page_size?: number
  class_id?: number
  name?: string
  student_no?: string
}) {
  return request.get<PageResponse<Student>>('/students', { params })
}

// 别名导出，兼容旧代码
export { getStudents as getStudentList }

// 搜索学生（支持学号或姓名）
export function searchStudents(query: string) {
  return request.get<PageResponse<Student>>('/students', {
    params: {
      page: 1,
      page_size: 20,
      // 同时搜索学号和姓名
      ...(query.match(/^\d/) ? { student_no: query } : { name: query })
    }
  })
}

// 获取学生详情
export function getStudent(id: number) {
  return request.get<Student>(`/students/${id}`)
}

// 获取学生成绩
export function getStudentScores(id: number, semester?: string) {
  return request.get<{ items: Score[]; total: number }>(`/students/${id}/scores`, {
    params: { semester }
  })
}

// 获取学生考勤
export function getStudentAttendances(id: number, semester?: string) {
  return request.get<{ items: Attendance[]; total: number }>(`/students/${id}/attendances`, {
    params: { semester }
  })
}

// ==================== 学生端专用接口 ====================

// 学生统计数据
export interface StudentStats {
  avgScore: number
  attendanceRate: number
  alertCount: number
  earnedCredits: number
}

// 成绩项
export interface GradeItem {
  id: number
  course_name: string
  course_code: string
  credit: number
  semester: string
  score: number
  grade_point: number
}

// 考勤记录
export interface AttendanceRecord {
  id: number
  course_name: string
  date: string
  week: number
  time: string
  status: 'normal' | 'late' | 'absent' | 'leave'
  remark?: string
}

// 考勤统计
export interface AttendanceStats {
  normal: number
  late: number
  absent: number
  leave: number
}

// 预警项
export interface AlertItem {
  id: number
  alert_type: 'grade' | 'attendance' | 'credit' | 'comprehensive'
  alert_level: 'high' | 'medium' | 'low'
  description: string
  suggestion?: string
  status: 'pending' | 'processing' | 'resolved'
  created_at: string
  updated_at?: string
}

// 预警统计
export interface AlertStats {
  total: number
  high: number
  medium: number
  low: number
}

/**
 * 获取当前登录学生的统计数据
 */
export function getStudentStats() {
  return request.get<StudentStats>('/students/me/stats')
}

/**
 * 获取当前登录学生的成绩列表
 */
export function getStudentGrades(params?: {
  semester?: string
  status?: 'pass' | 'fail'
}) {
  return request.get<{ items: GradeItem[]; total: number }>('/students/me/grades', { params })
}

/**
 * 获取当前登录学生的考勤记录
 */
export function getStudentAttendance(params?: {
  page?: number
  page_size?: number
  course?: string
  status?: string
  start_date?: string
  end_date?: string
}) {
  return request.get<{
    items: AttendanceRecord[]
    total: number
    stats?: AttendanceStats
  }>('/students/me/attendance', { params })
}

/**
 * 获取当前登录学生的预警列表
 */
export function getStudentAlerts(params?: {
  page?: number
  page_size?: number
  type?: string
  level?: string
  status?: string
}) {
  return request.get<{
    items: AlertItem[]
    total: number
    stats?: AlertStats
  }>('/students/me/alerts', { params })
}
