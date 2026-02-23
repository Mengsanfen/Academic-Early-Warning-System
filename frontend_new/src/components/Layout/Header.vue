<template>
  <div class="header">
    <div class="header-left">
      <el-icon
        class="collapse-btn"
        :size="20"
        @click="$emit('toggle')"
      >
        <component :is="isCollapsed ? 'Expand' : 'Fold'" />
      </el-icon>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
          {{ item.meta?.title }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="header-right">
      <el-dropdown @command="handleCommand">
        <div class="user-info">
          <el-avatar :size="32" :src="avatarUrl" class="user-avatar">
            {{ avatarText }}
          </el-avatar>
          <span class="user-name">{{ displayName }}</span>
          <el-icon><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              <el-tag size="small" :type="roleTagType">{{ roleText }}</el-tag>
            </el-dropdown-item>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              个人信息
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessageBox } from 'element-plus'
import { User } from '@element-plus/icons-vue'
import { getUserProfile } from '@/api/auth'
import type { UserProfile } from '@/types'

defineProps<{
  isCollapsed: boolean
}>()

defineEmits<{
  (e: 'toggle'): void
}>()

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const userProfile = ref<UserProfile | null>(null)

const breadcrumbs = computed(() => {
  return route.matched.filter(item => item.meta?.title && item.path !== '/')
})

const roleText = computed(() => {
  const roles: Record<string, string> = {
    admin: '管理员',
    counselor: '辅导员',
    student: '学生'
  }
  return roles[userStore.userInfo?.role || ''] || '未知'
})

const roleTagType = computed(() => {
  const types: Record<string, string> = {
    admin: 'danger',
    counselor: 'warning',
    student: 'info'
  }
  return types[userStore.userInfo?.role || '']
})

// 显示名称：优先显示昵称，其次姓名，最后用户名
const displayName = computed(() => {
  return userProfile.value?.nickname ||
    userStore.userInfo?.name ||
    userStore.userInfo?.username ||
    '用户'
})

// 头像文字（当没有头像时显示）
const avatarText = computed(() => {
  const name = displayName.value
  return name ? name.charAt(0).toUpperCase() : 'U'
})

// 头像URL
const avatarUrl = computed(() => {
  if (userProfile.value?.avatar_url) {
    if (userProfile.value.avatar_url.startsWith('/')) {
      return `http://localhost:8000${userProfile.value.avatar_url}`
    }
    return userProfile.value.avatar_url
  }
  return ''
})

// 获取用户详细信息（包含头像）
async function fetchUserProfile() {
  try {
    userProfile.value = await getUserProfile()
  } catch (error) {
    console.error('获取用户信息失败', error)
  }
}

function handleCommand(command: string) {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      userStore.logout()
    }).catch(() => {})
  } else if (command === 'profile') {
    router.push('/profile')
  }
}

onMounted(() => {
  fetchUserProfile()
})
</script>

<style lang="scss" scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;

  .collapse-btn {
    cursor: pointer;
    color: #606266;

    &:hover {
      color: #409EFF;
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background-color 0.2s;

  &:hover {
    background-color: #f5f7fa;
  }

  .user-avatar {
    background: linear-gradient(135deg, #409EFF, #66b1ff);
    color: #fff;
    font-weight: 600;
  }

  .user-name {
    font-size: 14px;
    color: #303133;
  }
}
</style>
