import { request } from '@/utils/request'
import type { PageResponse, User, UserRole } from '@/types'

// 获取用户列表
export function getUsers(params: {
  page?: number
  page_size?: number
  role?: UserRole
  search?: string
}) {
  return request.get<PageResponse<User>>('/users', { params })
}

// 创建用户
export function createUser(data: {
  username: string
  password: string
  role: UserRole
  student_id?: number
}) {
  return request.post<User>('/users', data)
}

// 更新用户
export function updateUser(id: number, data: {
  password?: string
  is_active?: boolean
}) {
  return request.put<User>(`/users/${id}`, data)
}

// 删除用户
export function deleteUser(id: number) {
  return request.delete(`/users/${id}`)
}
