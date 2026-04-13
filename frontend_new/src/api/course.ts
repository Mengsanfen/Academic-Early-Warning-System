import { request } from '@/utils/request'
import type { PageResponse, Course, CourseType } from '@/types'

// 获取课程列表
export function getCourses(params: {
  page?: number
  page_size?: number
  course_name?: string
  semester?: string
  course_type?: CourseType
  class_id?: number
}) {
  return request.get<PageResponse<Course>>('/courses', { params })
}

// 获取所有课程（不分页）
export function getAllCourses(params?: {
  semester?: string
  course_type?: CourseType
}) {
  return request.get<{ items: Course[] }>('/courses/all', { params })
}

// 获取课程详情
export function getCourse(id: number) {
  return request.get<Course>(`/courses/${id}`)
}

// 创建课程
export function createCourse(data: Partial<Course>) {
  return request.post<{ message: string; id: number }>('/courses', data)
}

// 更新课程
export function updateCourse(id: number, data: Partial<Course>) {
  return request.put<{ message: string }>(`/courses/${id}`, data)
}

// 批量更新课程类型
export function batchUpdateCourseType(courseIds: number[], courseType: CourseType) {
  return request.put<{ message: string; updated: number }>('/courses/batch/type', {
    course_ids: courseIds,
    course_type: courseType
  })
}

// 删除课程
export function deleteCourse(id: number) {
  return request.delete<{ message: string }>(`/courses/${id}`)
}

// 获取学期列表
export function getSemesters() {
  return request.get<{ items: string[] }>('/courses/semesters')
}

// 获取课程类型列表
export function getCourseTypes() {
  return request.get<{
    items: Array<{
      value: string
      label: string
      description: string
    }>
  }>('/courses/types')
}

// 获取课程统计
export function getCourseStatistics() {
  return request.get<{
    by_type: Array<{
      type: string
      type_name: string
      count: number
    }>
    by_semester: Array<{
      semester: string
      count: number
    }>
    total: number
  }>('/courses/statistics')
}
