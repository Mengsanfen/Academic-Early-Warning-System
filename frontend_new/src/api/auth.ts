import { request } from '@/utils/request'
import type {
  LoginRequest,
  LoginResponse,
  User,
  UserProfile,
  UserProfileUpdate,
  ChangePasswordRequest,
  SendCodeRequest,
  ResetPasswordRequest
} from '@/types'

// 登录
export function login(data: LoginRequest) {
  return request.post<LoginResponse>('/auth/login', data)
}

// 登出
export function logout() {
  return request.post('/auth/logout')
}

// 刷新token
export function refreshToken(refresh_token: string) {
  return request.post('/auth/refresh', { refresh_token })
}

// 获取当前用户信息（从auth/me获取，包含学生关联信息）
export function getCurrentUser() {
  return request.get<User>('/auth/me')
}

// 获取当前用户详细信息（包含个人资料）
export function getUserProfile() {
  return request.get<UserProfile>('/users/me')
}

// 更新个人信息
export function updateProfile(data: UserProfileUpdate) {
  return request.put<UserProfile>('/users/me', data)
}

// 上传头像
export function uploadAvatar(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ message: string; avatar_url: string }>('/users/me/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 修改密码
export function changePassword(data: ChangePasswordRequest) {
  return request.post('/auth/change-password', data)
}

// 发送验证码
export function sendVerificationCode(data: SendCodeRequest) {
  return request.post<{ message: string }>('/password/send-code', data)
}

// 重置密码
export function resetPassword(data: ResetPasswordRequest) {
  return request.post<{ message: string }>('/password/reset', data)
}
