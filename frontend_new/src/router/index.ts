import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'
import type { UserRole } from '@/types'

// 路由元信息类型
declare module 'vue-router' {
  interface RouteMeta {
    title: string
    icon?: string
    hidden?: boolean
    requiresAuth?: boolean
    roles?: UserRole[]  // 允许访问的角色列表
  }
}

/**
 * 路由配置
 * roles 字段控制权限：
 * - 不设置 roles: 所有登录用户可访问
 * - 设置 roles: 只有指定角色可访问
 */
const routes: RouteRecordRaw[] = [
  // ========== 公开页面 ==========
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/login/forgot-password.vue'),
    meta: { title: '找回密码', requiresAuth: false }
  },

  // ========== 管理后台（管理员/辅导员） ==========
  {
    path: '/',
    component: () => import('@/components/Layout/index.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      // 仪表盘 - 管理员/辅导员
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: {
          title: '仪表盘',
          icon: 'DataAnalysis',
          roles: ['admin', 'counselor']
        }
      },
      // 学生管理 - 管理员/辅导员
      {
        path: 'students',
        name: 'Students',
        component: () => import('@/views/students/index.vue'),
        meta: {
          title: '学生管理',
          icon: 'User',
          roles: ['admin', 'counselor']
        }
      },
      {
        path: 'students/:id',
        name: 'StudentDetail',
        component: () => import('@/views/students/detail.vue'),
        meta: {
          title: '学生详情',
          hidden: true,
          roles: ['admin', 'counselor']
        }
      },
      // 规则配置 - 仅管理员
      {
        path: 'rules',
        name: 'Rules',
        component: () => import('@/views/rules/index.vue'),
        meta: {
          title: '规则配置',
          icon: 'Setting',
          roles: ['admin']
        }
      },
      // 预警中心 - 管理员/辅导员
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/alerts/AlertCenterEnhanced.vue'),
        meta: {
          title: '预警中心',
          icon: 'Bell',
          roles: ['admin', 'counselor']
        }
      },
      // 用户管理 - 仅管理员
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/UsersEnhanced.vue'),
        meta: {
          title: '用户管理',
          icon: 'Avatar',
          roles: ['admin']
        }
      },
      // 成绩管理 - 管理员/辅导员
      {
        path: 'scores',
        name: 'Scores',
        component: () => import('@/views/scores/index.vue'),
        meta: {
          title: '成绩管理',
          icon: 'TrendCharts',
          roles: ['admin', 'counselor']
        }
      },
      // 考勤管理 - 管理员/辅导员
      {
        path: 'attendances',
        name: 'Attendances',
        component: () => import('@/views/attendances/index.vue'),
        meta: {
          title: '考勤管理',
          icon: 'Calendar',
          roles: ['admin', 'counselor']
        }
      },
      // 个人信息 - 所有用户
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/profile/index.vue'),
        meta: { title: '个人信息', hidden: true }
      }
    ]
  },

  // ========== 学生端 ==========
  {
    path: '/student',
    component: () => import('@/components/Layout/index.vue'),
    redirect: '/student/overview',
    meta: { requiresAuth: true },
    children: [
      // 个人概览 - 学生
      {
        path: 'overview',
        name: 'StudentOverview',
        component: () => import('@/views/student/Overview.vue'),
        meta: {
          title: '个人概览',
          icon: 'DataAnalysis',
          roles: ['student']
        }
      },
      // 我的成绩 - 学生
      {
        path: 'grades',
        name: 'StudentGrades',
        component: () => import('@/views/student/Grades.vue'),
        meta: {
          title: '我的成绩',
          icon: 'Document',
          roles: ['student']
        }
      },
      // 我的考勤 - 学生
      {
        path: 'attendance',
        name: 'StudentAttendance',
        component: () => import('@/views/student/Attendance.vue'),
        meta: {
          title: '我的考勤',
          icon: 'Calendar',
          roles: ['student']
        }
      },
      // 我的预警 - 学生
      {
        path: 'my-alerts',
        name: 'StudentAlerts',
        component: () => import('@/views/student/StudentAlertsEnhanced.vue'),
        meta: {
          title: '我的预警',
          icon: 'Warning',
          roles: ['student']
        }
      }
    ]
  },

  // ========== 404 ==========
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '404' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  // 设置页面标题
  document.title = `${to.meta.title || '学业预警系统'} - 学业预警系统`

  const userStore = useUserStore()

  // 不需要认证的页面
  if (to.meta.requiresAuth === false) {
    // 已登录用户访问登录页，根据角色跳转
    if (to.path === '/login' && userStore.isLoggedIn) {
      redirectToHome(userStore.userInfo?.role, next)
      return
    }
    next()
    return
  }

  // 需要认证的页面
  if (!userStore.isLoggedIn) {
    next('/login')
    return
  }

  // 获取用户信息
  if (!userStore.userInfo) {
    try {
      await userStore.fetchUserInfo()
    } catch (error) {
      next('/login')
      return
    }
  }

  // 角色权限检查
  const requiredRoles = to.meta.roles
  const userRole = userStore.userInfo?.role

  if (requiredRoles && requiredRoles.length > 0) {
    if (!userRole || !requiredRoles.includes(userRole)) {
      // 无权限，重定向到对应角色的首页
      redirectToHome(userRole, next)
      return
    }
  }

  next()
})

/**
 * 根据用户角色重定向到对应的首页
 */
function redirectToHome(role: UserRole | undefined, next: any) {
  switch (role) {
    case 'admin':
    case 'counselor':
      next('/dashboard')
      break
    case 'student':
      next('/student/overview')
      break
    default:
      next('/login')
  }
}

export default router
