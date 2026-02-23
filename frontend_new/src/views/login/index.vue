<template>
  <div class="login-container">
    <div class="login-bg">
      <div class="bg-shape shape-1"></div>
      <div class="bg-shape shape-2"></div>
      <div class="bg-shape shape-3"></div>
    </div>

    <div class="login-card">
      <div class="login-header">
        <div class="logo">
          <el-icon :size="48" color="#409EFF"><Warning /></el-icon>
        </div>
        <h1 class="title">学业预警系统</h1>
        <p class="subtitle">基于多源数据与规则引擎的学业预警管理平台</p>
      </div>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <div class="form-options">
            <el-button link type="primary" @click="goForgotPassword">
              忘记密码？
            </el-button>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <p>测试账号</p>
        <div class="test-accounts">
          <el-tag>admin / admin123 (管理员)</el-tag>
          <el-tag type="warning">counselor / counselor123 (辅导员)</el-tag>
        </div>
        <p style="margin-top: 8px; font-size: 11px; color: #909399;">学生账号请通过管理员批量导入创建</p>
      </div>
    </div>

    <!-- 首次登录修改密码对话框 -->
    <ChangePasswordDialog
      v-model="showChangePassword"
      @success="handlePasswordChanged"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { User, Lock, Warning } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import ChangePasswordDialog from '@/components/ChangePasswordDialog.vue'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const showChangePassword = ref(false)

const formData = reactive({
  username: '',
  password: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

async function handleLogin() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  loading.value = true
  try {
    const response = await userStore.login(formData.username, formData.password)

    // 检查是否需要修改密码
    if (response.require_password_change) {
      showChangePassword.value = true
    } else {
      ElMessage.success('登录成功')
      router.push('/dashboard')
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

// 密码修改成功后跳转
function handlePasswordChanged() {
  ElMessage.success('登录成功')
  router.push('/dashboard')
}

// 跳转忘记密码页面
function goForgotPassword() {
  router.push('/forgot-password')
}
</script>

<style lang="scss" scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;

  .bg-shape {
    position: absolute;
    border-radius: 50%;
    opacity: 0.1;

    &.shape-1 {
      width: 600px;
      height: 600px;
      background: #fff;
      top: -200px;
      left: -200px;
    }

    &.shape-2 {
      width: 400px;
      height: 400px;
      background: #fff;
      bottom: -100px;
      right: -100px;
    }

    &.shape-3 {
      width: 300px;
      height: 300px;
      background: #fff;
      top: 50%;
      right: 20%;
    }
  }
}

.login-card {
  width: 420px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  position: relative;
  z-index: 1;
}

.login-header {
  text-align: center;
  margin-bottom: 40px;

  .logo {
    margin-bottom: 16px;
  }

  .title {
    font-size: 28px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 8px;
  }

  .subtitle {
    font-size: 14px;
    color: #909399;
    margin: 0;
  }
}

.login-form {
  .form-options {
    display: flex;
    justify-content: flex-end;
    width: 100%;
  }

  .login-btn {
    width: 100%;
    height: 44px;
    font-size: 16px;
  }
}

.login-footer {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
  text-align: center;

  p {
    font-size: 12px;
    color: #909399;
    margin-bottom: 12px;
  }

  .test-accounts {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }
}
</style>
