import { request } from '@/utils/request'

// 获取成绩列表
export function getScoreList(params: {
  page?: number
  page_size?: number
  student_no?: string
  student_name?: string
  course_name?: string
  semester?: string
  is_passed?: boolean | null
  class_id?: number
}) {
  return request.get('/scores', { params })
}

// 获取课程列表（用于下拉框）
export function getScoreCourses(semester?: string) {
  return request.get('/scores/courses', { params: { semester } })
}

// 获取学期列表
export function getScoreSemesters() {
  return request.get('/scores/semesters')
}

// 创建成绩
export function createScore(data: {
  student_id: number
  course_id: number
  score: number
  semester: string
  exam_type?: string
}) {
  return request.post('/scores', data)
}

// 更新成绩
export function updateScore(id: number, data: {
  score: number
  exam_type?: string
}) {
  return request.put(`/scores/${id}`, data)
}

// 删除成绩
export function deleteScore(id: number) {
  return request.delete(`/scores/${id}`)
}

// 批量录入成绩
export function batchCreateScores(data: Array<{
  student_id: number
  course_id: number
  score: number
  semester: string
  exam_type?: string
}>) {
  return request.post('/scores/batch', data)
}
