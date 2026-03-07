import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, UserRole } from '@/types'
import { login as loginApi, logout as logoutApi, getCurrentUser } from '@/api/auth'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref<string>(localStorage.getItem('token') || '')
  const refreshToken = ref<string>(localStorage.getItem('refreshToken') || '')
  const userInfo = ref<User | null>(null)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const userRole = computed(() => userInfo.value?.role)
  const isAdmin = computed(() => userInfo.value?.role === 'admin')
  const isCounselor = computed(() => userInfo.value?.role === 'counselor')
  const isStudent = computed(() => userInfo.value?.role === 'student')

  // 登录
  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    token.value = res.access_token
    refreshToken.value = res.refresh_token
    userInfo.value = res.user
    
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('refreshToken', res.refresh_token)
    
    return res
  }

  // 登出
  function logout() {
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    router.push('/login')
  }

  // 获取用户信息
  async function fetchUserInfo() {
    try {
      const user = await getCurrentUser()
      userInfo.value = user
      return user
    } catch (error) {
      logout()
      throw error
    }
  }

  return {
    token,
    refreshToken,
    userInfo,
    isLoggedIn,
    userRole,
    isAdmin,
    isCounselor,
    isStudent,
    login,
    logout,
    fetchUserInfo
  }
})
