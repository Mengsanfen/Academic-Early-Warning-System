export type UserRole = 'admin' | 'counselor' | 'student'

export const USER_ROLES = {
  ADMIN: 'admin' as UserRole,
  COUNSELOR: 'counselor' as UserRole,
  STUDENT: 'student' as UserRole,
}

export type AlertStatus = 'pending' | 'processing' | 'resolved' | 'ignored'

export const ALERT_STATUSES = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  RESOLVED: 'resolved',
  IGNORED: 'ignored',
} as const

export type AlertLevel = 'warning' | 'serious' | 'urgent'

export const ALERT_LEVELS = {
  WARNING: 'warning',
  SERIOUS: 'serious',
  URGENT: 'urgent',
} as const

export type RuleType = 'score' | 'attendance' | 'graduation'

export const RULE_TYPES = {
  SCORE: 'score',
  ATTENDANCE: 'attendance',
  GRADUATION: 'graduation',
} as const

export type TargetType = 'all' | 'grades' | 'classes'

export const TARGET_TYPES = {
  ALL: 'all',
  GRADES: 'grades',
  CLASSES: 'classes',
} as const

export type CourseType = 'required' | 'elective' | 'public' | 'professional' | 'practice'

export const COURSE_TYPES = {
  REQUIRED: 'required' as CourseType,
  ELECTIVE: 'elective' as CourseType,
  PUBLIC: 'public' as CourseType,
  PROFESSIONAL: 'professional' as CourseType,
  PRACTICE: 'practice' as CourseType,
} as const

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
  student?: {
    id: number
    name: string
    student_no: string
    class_name?: string
    phone?: string
    avatar?: string
  }
}

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
  student_name?: string
  student_no?: string
  class_name?: string
}

export interface UserProfileUpdate {
  nickname?: string
  email?: string
  phone?: string
  bio?: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
  require_password_change?: boolean
}

export interface ChangePasswordRequest {
  old_password?: string
  new_password: string
}

export interface SendCodeRequest {
  email: string
}

export interface ResetPasswordRequest {
  email: string
  code: string
  new_password: string
}

export interface ImportResult {
  total: number
  success: number
  failed: number
  errors: string[]
  created_users: number
}

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

export interface Score {
  id: number
  course_name: string
  course_code?: string
  credit?: number
  score: number
  semester: string
  is_passed: boolean
}

export interface Attendance {
  id: number
  course_name: string
  date: string
  status: string
}

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
  target_type: TargetType
  target_grades?: string[] | null
  target_classes?: number[] | null
}

export interface Course {
  id: number
  course_code: string
  course_name: string
  credit: number
  semester: string
  class_id?: number
  class_name?: string | null
  grade?: string | null
  department_name?: string | null
  teacher_name?: string
  course_type: CourseType
  course_type_name?: string
}

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
    code?: string
    type: string
    level: string
    description?: string
    conditions?: Record<string, any>
    message_template?: string
  }
  records: AlertRecord[]
}

export type ElementTagType = '' | 'success' | 'warning' | 'info' | 'primary' | 'danger'

export interface AlertRecord {
  id: number
  handler_name?: string
  action: string
  result?: string
  created_at: string
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

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

export interface TrendData {
  days: number
  data: Array<{
    date: string
    count: number
  }>
}

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
