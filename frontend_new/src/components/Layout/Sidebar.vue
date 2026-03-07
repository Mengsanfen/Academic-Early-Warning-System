<template>
  <div class="sidebar">
    <div class="logo">
      <el-icon :size="28"><Warning /></el-icon>
      <span v-show="!isCollapsed" class="logo-text">学业预警系统</span>
    </div>

    <el-menu
      :default-active="activeMenu"
      :collapse="isCollapsed"
      :collapse-transition="false"
      background-color="transparent"
      text-color="#fff"
      active-text-color="#409EFF"
      router
    >
      <template v-for="item in visibleMenuItems" :key="item.path">
        <el-menu-item :index="item.path">
          <el-icon>
            <component :is="getIconComponent(item.meta?.icon)" />
          </el-icon>
          <template #title>{{ item.meta?.title }}</template>
        </el-menu-item>
      </template>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  Warning,
  DataAnalysis,
  User,
  Setting,
  Bell,
  Avatar,
  Document,
  Calendar,
  TrendCharts
} from '@element-plus/icons-vue'
import type { UserRole } from '@/types'

defineProps<{
  isCollapsed: boolean
}>()

const route = useRoute()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)

// 图标映射
const iconMap: Record<string, any> = {
  DataAnalysis,
  User,
  Setting,
  Bell,
  Avatar,
  Warning,
  Document,
  Calendar,
  TrendCharts
}

// 获取图标组件
const getIconComponent = (iconName?: string) => {
  if (!iconName) return Warning
  return iconMap[iconName] || Warning
}

// 根据角色定义菜单配置
const menuConfig: Record<UserRole, { basePath: string; items: any[] }> = {
  // 管理员菜单
  admin: {
    basePath: '/',
    items: [
      { path: '/dashboard', title: '仪表盘', icon: 'DataAnalysis' },
      { path: '/students', title: '学生管理', icon: 'User' },
      { path: '/scores', title: '成绩管理', icon: 'TrendCharts' },
      { path: '/attendances', title: '考勤管理', icon: 'Calendar' },
      { path: '/rules', title: '规则配置', icon: 'Setting' },
      { path: '/alerts', title: '预警中心', icon: 'Bell' },
      { path: '/users', title: '用户管理', icon: 'Avatar' }
    ]
  },
  // 辅导员菜单
  counselor: {
    basePath: '/',
    items: [
      { path: '/dashboard', title: '仪表盘', icon: 'DataAnalysis' },
      { path: '/students', title: '学生管理', icon: 'User' },
      { path: '/scores', title: '成绩管理', icon: 'TrendCharts' },
      { path: '/attendances', title: '考勤管理', icon: 'Calendar' },
      { path: '/alerts', title: '预警中心', icon: 'Bell' }
    ]
  },
  // 学生菜单
  student: {
    basePath: '/student',
    items: [
      { path: '/student/overview', title: '个人概览', icon: 'DataAnalysis' },
      { path: '/student/grades', title: '我的成绩', icon: 'Document' },
      { path: '/student/attendance', title: '我的考勤', icon: 'Calendar' },
      { path: '/student/my-alerts', title: '我的预警', icon: 'Warning' }
    ]
  }
}

// 计算可见的菜单项
const visibleMenuItems = computed(() => {
  const role = userStore.userInfo?.role as UserRole | undefined

  if (!role || !menuConfig[role]) {
    return []
  }

  const config = menuConfig[role]
  return config.items.map(item => ({
    path: item.path,
    meta: {
      title: item.title,
      icon: item.icon
    }
  }))
})
</script>

<style lang="scss" scoped>
.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);

  .logo-text {
    white-space: nowrap;
  }
}

.el-menu {
  border-right: none;

  .el-menu-item {
    margin: 4px 8px;
    border-radius: 8px;

    &:hover {
      background-color: rgba(255, 255, 255, 0.1) !important;
    }

    &.is-active {
      background: linear-gradient(90deg, #409EFF, #66b1ff) !important;
      color: #fff !important;
    }
  }
}
</style>
