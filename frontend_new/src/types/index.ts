// 用户角色
export type UserRole = 'admin' | 'counselor' | 'student'

// 角色常量（用于代码中引用）
export const USER_ROLES = {
  ADMIN: 'admin' as UserRole,
  COUNSELOR: 'counselor' as UserRole,
  STUDENT: 'student' as UserRole
}

// 预警状态
export enum AlertStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  RESOLVED = 'resolved',
  IGNORED = 'ignored'
}

// 预警级别
export enum AlertLevel {
  WARNING = 'warning',
  SERIOUS = 'serious',
  URGENT = 'urgent'
}

// 规则类型
export enum RuleType {
  SCORE = 'score',
  ATTENDANCE = 'attendance',
  GRADUATION = 'graduation'
}

// 用户信息
export interface User {
  id: number
  username: string
  role: UserRole
  nickname?: string
  name?: string
  is_active?: boolean
  first_login?: boolean
  email?: string
  student_id?: number
  // 关联的学生信息（学生角色才有）
  student?: {
    id: number
    name: string
    student_no: string
    class_name?: string
    phone?: string
    avatar?: string
  }
}

// 用户详细信息（个人信息页面）
export interface UserProfile {
  id: number
  username: string
  role: UserRole
  nickname?: string
  avatar_url?: string
  email?: string
  phone?: string
  bio?: string
  is_active: boolean
  first_login: boolean
  created_at?: string
  // 关联的学生信息
  student_name?: string
  student_no?: string
  class_name?: string
}

// 更新个人信息请求
export interface UserProfileUpdate {
  nickname?: string
  email?: string
  phone?: string
  bio?: string
}

// 登录请求
export interface LoginRequest {
  username: string
  password: string
}

// 登录响应
export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
  require_password_change?: boolean
}

// 修改密码请求
export interface ChangePasswordRequest {
  old_password?: string
  new_password: string
}

// 发送验证码请求
export interface SendCodeRequest {
  email: string
}

// 重置密码请求
export interface ResetPasswordRequest {
  email: string
  code: string
  new_password: string
}

// 导入结果
export interface ImportResult {
  total: number
  success: number
  failed: number
  errors: string[]
  created_users: number
}

// 学生信息
export interface Student {
  id: number
  student_no: string
  name: string
  gender?: string
  class_id: number
  class_name?: string
  enroll_year?: number
  phone?: string
  email?: string
  status: string
}

// 成绩信息
export interface Score {
  id: number
  course_name: string
  course_code?: string
  credit?: number
  score: number
  semester: string
  is_passed: boolean
}

// 考勤信息
export interface Attendance {
  id: number
  course_name: string
  date: string
  status: string
}

// 规则信息
export interface Rule {
  id: number
  name: string
  code: string
  type: RuleType
  conditions: Record<string, any>
  level: AlertLevel
  description?: string
  message_template?: string
  is_active: boolean
}

// 预警信息
export interface Alert {
  id: number
  student_id: number
  student_name?: string
  student_no?: string
  class_name?: string
  rule_id: number
  rule_name?: string
  rule_type?: string
  level: AlertLevel
  message: string
  status: AlertStatus
  created_at: string
}

// 预警详情
export interface AlertDetail extends Alert {
  student?: {
    id: number
    student_no: string
    name: string
    class_name?: string
    phone?: string
    email?: string
  }
  rule?: {
    id: number
    name: string
    type: string
    level: string
  }
  records: AlertRecord[]
}

// 预警处理记录
export interface AlertRecord {
  id: number
  handler_name?: string
  action: string
  result?: string
  created_at: string
}

// 分页响应
export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// 仪表盘数据
export interface DashboardOverview {
  student_count: number
  alert_count: {
    total: number
    pending: number
    processing: number
    resolved: number
  }
  alert_by_level: Record<string, number>
  alert_by_type: Record<string, number>
  recent_alerts: Alert[]
}

// 预警趋势数据
export interface TrendData {
  days: number
  data: Array<{
    date: string
    count: number
  }>
}

// 预警分布数据
export interface DistributionData {
  by_class: Array<{
    class_name: string
    count: number
  }>
  by_type: Array<{
    type: string
    count: number
  }>
}
