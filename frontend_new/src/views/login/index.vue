<template>
  <div class="login-container">
    <!-- 粒子画布 -->
    <canvas ref="particleCanvas" class="particle-canvas"></canvas>

    <!-- 左侧品牌区域 -->
    <div class="brand-section">
      <div class="brand-content">
        <div class="brand-logo">
          <el-icon :size="56" color="#fff"><Warning /></el-icon>
        </div>
        <h1 class="brand-title">学业预警系统</h1>
        <p class="brand-subtitle">Academic Early Warning System</p>
        <div class="brand-divider"></div>
        <p class="brand-desc">
          基于多源数据融合与智能规则引擎<br />
          为高校学生学业保驾护航
        </p>
        <div class="brand-features">
          <div class="feature-item">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据驱动</span>
          </div>
          <div class="feature-item">
            <el-icon><Monitor /></el-icon>
            <span>实时预警</span>
          </div>
          <div class="feature-item">
            <el-icon><Setting /></el-icon>
            <span>智能分析</span>
          </div>
        </div>
      </div>
      <!-- 底部版权 -->
      <div class="brand-footer">
        <span>© 2024 智慧校园教育平台</span>
      </div>
    </div>

    <!-- 右侧登录区域 -->
    <div class="login-section">
      <div class="login-wrapper">
        <div class="login-header">
          <h2 class="login-title">欢迎登录</h2>
          <p class="login-subtitle">请输入您的账号信息</p>
        </div>

        <el-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          class="login-form"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username">
            <div class="form-label">用户名</div>
            <el-input
              v-model="formData.username"
              placeholder="请输入用户名"
              size="large"
              :prefix-icon="User"
            />
          </el-form-item>

          <el-form-item prop="password">
            <div class="form-label">密码</div>
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
              <el-checkbox v-model="rememberMe">记住登录状态</el-checkbox>
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
              <span v-if="!loading">登 录</span>
              <span v-else>登录中...</span>
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login-footer">
          <div class="divider">
            <span>测试账号</span>
          </div>
          <div class="test-accounts">
            <div class="account-item">
              <span class="account-role">管理员</span>
              <span class="account-info">admin / admin123</span>
            </div>
            <div class="account-item">
              <span class="account-role">辅导员</span>
              <span class="account-info">counselor / counselor123</span>
            </div>
          </div>
          <p class="account-tip">学生账号请通过管理员批量导入创建</p>
        </div>
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
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { User, Lock, Warning, DataAnalysis, Monitor, Setting } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import ChangePasswordDialog from '@/components/ChangePasswordDialog.vue'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const showChangePassword = ref(false)
const rememberMe = ref(false)
const particleCanvas = ref<HTMLCanvasElement | null>(null)

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

// 粒子系统
interface Particle {
  x: number
  y: number
  size: number
  speedX: number
  speedY: number
  opacity: number
  color: string
}

let particles: Particle[] = []
let animationId: number | null = null
let ctx: CanvasRenderingContext2D | null = null

const colors = [
  'rgba(255, 255, 255, 0.6)',
  'rgba(64, 158, 255, 0.5)',
  'rgba(103, 194, 122, 0.4)',
  'rgba(144, 202, 249, 0.4)'
]

function initParticles() {
  if (!particleCanvas.value) return
  const canvas = particleCanvas.value
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
  ctx = canvas.getContext('2d')

  particles = []
  const particleCount = Math.floor((canvas.width * canvas.height) / 15000)

  for (let i = 0; i < particleCount; i++) {
    particles.push(createParticle(canvas))
  }
}

function createParticle(canvas: HTMLCanvasElement): Particle {
  return {
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    size: Math.random() * 2 + 0.5,
    speedX: (Math.random() - 0.5) * 0.3,
    speedY: (Math.random() - 0.5) * 0.3,
    opacity: Math.random() * 0.4 + 0.1,
    color: colors[Math.floor(Math.random() * colors.length)]
  }
}

function drawParticles() {
  if (!ctx || !particleCanvas.value) return
  const canvas = particleCanvas.value

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  particles.forEach((particle, index) => {
    particle.x += particle.speedX
    particle.y += particle.speedY

    if (particle.x < 0) particle.x = canvas.width
    if (particle.x > canvas.width) particle.x = 0
    if (particle.y < 0) particle.y = canvas.height
    if (particle.y > canvas.height) particle.y = 0

    ctx!.beginPath()
    ctx!.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2)
    ctx!.fillStyle = particle.color
    ctx!.fill()

    particles.slice(index + 1).forEach(otherParticle => {
      const dx = particle.x - otherParticle.x
      const dy = particle.y - otherParticle.y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < 100) {
        ctx!.beginPath()
        ctx!.moveTo(particle.x, particle.y)
        ctx!.lineTo(otherParticle.x, otherParticle.y)
        ctx!.strokeStyle = `rgba(255, 255, 255, ${0.08 * (1 - distance / 100)})`
        ctx!.lineWidth = 0.5
        ctx!.stroke()
      }
    })
  })

  animationId = requestAnimationFrame(drawParticles)
}

function handleResize() {
  if (!particleCanvas.value) return
  const canvas = particleCanvas.value
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
  initParticles()
}

onMounted(() => {
  initParticles()
  drawParticles()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('resize', handleResize)
})

async function handleLogin() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  loading.value = true
  try {
    const response = await userStore.login(formData.username, formData.password)

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

function handlePasswordChanged() {
  ElMessage.success('登录成功')
  router.push('/dashboard')
}

function goForgotPassword() {
  router.push('/forgot-password')
}
</script>

<style lang="scss" scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  position: relative;
  overflow: hidden;
}

// 粒子画布
.particle-canvas {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

// 左侧品牌区域
.brand-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 60px;
  position: relative;
  z-index: 1;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image: url('@/assets/images/login-bg.jpg');
    background-size: cover;
    background-position: center;
    z-index: 0;
  }

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
      135deg,
      rgba(26, 54, 93, 0.25) 0%,
      rgba(37, 99, 235, 0.15) 50%,
      rgba(30, 64, 175, 0.2) 100%
    );
    z-index: 1;
  }
}

.brand-content {
  position: relative;
  z-index: 2;
  text-align: center;
  color: #fff;
  max-width: 480px;
}

.brand-logo {
  width: 100px;
  height: 100px;
  background: rgba(26, 54, 93, 0.75);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 32px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.brand-title {
  font-size: 42px;
  font-weight: 700;
  margin: 0 0 12px;
  letter-spacing: 4px;
  color: #fff;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
}

.brand-subtitle {
  font-size: 16px;
  opacity: 0.85;
  letter-spacing: 3px;
  margin: 0 0 32px;
  font-weight: 300;
}

.brand-divider {
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.8), transparent);
  margin: 0 auto 32px;
  border-radius: 2px;
}

.brand-desc {
  font-size: 16px;
  line-height: 1.8;
  opacity: 0.9;
  margin: 0 0 48px;
  font-weight: 300;
}

.brand-features {
  display: flex;
  justify-content: center;
  gap: 48px;

  .feature-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;

    .el-icon {
      font-size: 32px;
      opacity: 0.9;
    }

    span {
      font-size: 14px;
      opacity: 0.85;
      letter-spacing: 1px;
    }
  }
}

.brand-footer {
  position: absolute;
  bottom: 24px;
  left: 0;
  right: 0;
  text-align: center;
  z-index: 2;

  span {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
    letter-spacing: 1px;
  }
}

// 右侧登录区域
.login-section {
  width: 520px;
  min-width: 520px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 2;
  box-shadow: -10px 0 40px rgba(0, 0, 0, 0.1);
}

.login-wrapper {
  width: 100%;
  max-width: 380px;
  padding: 40px;
}

.login-header {
  margin-bottom: 40px;

  .login-title {
    font-size: 28px;
    font-weight: 600;
    color: #1a1a1a;
    margin: 0 0 12px;
    letter-spacing: 1px;
  }

  .login-subtitle {
    font-size: 14px;
    color: #909399;
    margin: 0;
  }
}

.login-form {
  .form-label {
    font-size: 14px;
    font-weight: 500;
    color: #303133;
    margin-bottom: 8px;
  }

  .el-form-item {
    margin-bottom: 24px;
  }

  :deep(.el-input__wrapper) {
    border-radius: 8px;
    padding: 4px 15px;
    box-shadow: 0 0 0 1px #dcdfe6 inset;
    transition: all 0.2s;

    &:hover {
      box-shadow: 0 0 0 1px #c0c4cc inset;
    }

    &.is-focus {
      box-shadow: 0 0 0 1px #409eff inset;
    }
  }

  :deep(.el-input__inner) {
    height: 44px;
    line-height: 44px;
  }

  :deep(.el-input__prefix) {
    color: #c0c4cc;
  }

  .form-options {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;

    :deep(.el-checkbox__label) {
      color: #606266;
      font-size: 13px;
    }
  }

  .login-btn {
    width: 100%;
    height: 48px;
    font-size: 16px;
    font-weight: 500;
    border-radius: 8px;
    background: linear-gradient(135deg, #1a365d 0%, #2563eb 100%);
    border: none;
    letter-spacing: 8px;
    transition: all 0.3s;

    &:hover {
      background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }

    &:active {
      transform: translateY(0);
    }
  }
}

.login-footer {
  margin-top: 40px;

  .divider {
    display: flex;
    align-items: center;
    margin-bottom: 20px;

    &::before,
    &::after {
      content: '';
      flex: 1;
      height: 1px;
      background: #e4e7ed;
    }

    span {
      padding: 0 16px;
      font-size: 12px;
      color: #909399;
    }
  }

  .test-accounts {
    background: #f5f7fa;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;

    .account-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;

      &:not(:last-child) {
        border-bottom: 1px dashed #e4e7ed;
      }

      .account-role {
        font-size: 13px;
        color: #606266;
        font-weight: 500;

        &::before {
          content: '';
          display: inline-block;
          width: 6px;
          height: 6px;
          background: #409eff;
          border-radius: 50%;
          margin-right: 8px;
        }
      }

      .account-info {
        font-size: 12px;
        color: #909399;
        font-family: 'Monaco', 'Menlo', monospace;
      }
    }
  }

  .account-tip {
    font-size: 12px;
    color: #c0c4cc;
    text-align: center;
    margin: 0;
  }
}

// 响应式适配
@media (max-width: 1024px) {
  .brand-section {
    display: none;
  }

  .login-section {
    width: 100%;
    min-width: 100%;
  }

  .login-wrapper {
    max-width: 420px;
  }
}

@media (max-width: 480px) {
  .login-wrapper {
    padding: 24px;
  }

  .login-header {
    .login-title {
      font-size: 24px;
    }
  }
}
</style>