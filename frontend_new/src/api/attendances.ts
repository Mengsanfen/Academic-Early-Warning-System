import { request } from '@/utils/request'

// 获取考勤列表
export function getAttendanceList(params: {
  page?: number
  page_size?: number
  student_no?: string
  student_name?: string
  course_name?: string
  status?: string
  start_date?: string
  end_date?: string
  class_id?: number
}) {
  return request.get('/attendances', { params })
}

// 获取考勤统计
export function getAttendanceStats(params?: {
  student_id?: number
  class_id?: number
  start_date?: string
  end_date?: string
}) {
  return request.get('/attendances/stats', { params })
}

// 获取课程列表（用于下拉框）
export function getAttendanceCourses() {
  return request.get('/attendances/courses')
}

// 创建考勤记录
export function createAttendance(data: {
  student_id: number
  course_id: number
  date: string
  status: string
  remark?: string
}) {
  return request.post('/attendances', data)
}

// 更新考勤记录
export function updateAttendance(id: number, data: {
  status?: string
  remark?: string
}) {
  return request.put(`/attendances/${id}`, data)
}

// 删除考勤记录
export function deleteAttendance(id: number) {
  return request.delete(`/attendances/${id}`)
}

// 批量录入考勤
export function batchCreateAttendances(data: Array<{
  student_id: number
  course_id: number
  date: string
  status: string
  remark?: string
}>) {
  return request.post('/attendances/batch', data)
}
