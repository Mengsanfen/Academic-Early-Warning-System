<template>
  <div class="forgot-password-page">
    <div class="forgot-password-container">
      <div class="forgot-password-header">
        <h2>找回密码</h2>
        <p>通过邮箱验证码重置您的密码</p>
      </div>

      <!-- 步骤指示器 -->
      <el-steps :active="currentStep" finish-status="success" simple class="steps">
        <el-step title="输入邮箱" />
        <el-step title="验证身份" />
        <el-step title="重置密码" />
      </el-steps>

      <!-- 步骤1：输入邮箱 -->
      <div v-show="currentStep === 0" class="step-content">
        <el-form
          ref="emailFormRef"
          :model="emailForm"
          :rules="emailRules"
          label-position="top"
        >
          <el-form-item label="注册邮箱" prop="email">
            <el-input
              v-model="emailForm.email"
              placeholder="请输入您注册时使用的邮箱"
              prefix-icon="Message"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="sendingCode"
              @click="handleSendCode"
              style="width: 100%"
            >
              发送验证码
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 步骤2：输入验证码 -->
      <div v-show="currentStep === 1" class="step-content">
        <el-form
          ref="codeFormRef"
          :model="codeForm"
          :rules="codeRules"
          label-position="top"
        >
          <div class="email-display">
            <span>验证码已发送至：</span>
            <strong>{{ emailForm.email }}</strong>
          </div>

          <el-form-item label="验证码" prop="code">
            <el-input
              v-model="codeForm.code"
              placeholder="请输入6位验证码"
              maxlength="6"
              prefix-icon="Key"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="verifying"
              @click="handleVerifyCode"
              style="width: 100%"
            >
              验证
            </el-button>
          </el-form-item>

          <div class="resend-row">
            <span v-if="countdown > 0">{{ countdown }}秒后可重新发送</span>
            <el-button
              v-else
              link
              type="primary"
              @click="handleSendCode"
            >
              重新发送验证码
            </el-button>
          </div>
        </el-form>
      </div>

      <!-- 步骤3：重置密码 -->
      <div v-show="currentStep === 2" class="step-content">
        <el-form
          ref="passwordFormRef"
          :model="passwordForm"
          :rules="passwordRules"
          label-position="top"
        >
          <el-form-item label="新密码" prop="newPassword">
            <el-input
              v-model="passwordForm.newPassword"
              type="password"
              placeholder="请输入新密码（6-20位）"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="passwordForm.confirmPassword"
              type="password"
              placeholder="请再次输入新密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="resetting"
              @click="handleResetPassword"
              style="width: 100%"
            >
              重置密码
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 返回登录 -->
      <div class="back-to-login">
        <el-button link type="primary" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回登录
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { sendVerificationCode, resetPassword } from '@/api/auth'

const router = useRouter()

// 当前步骤
const currentStep = ref(0)

// 倒计时
const countdown = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

// 邮箱表单
const emailFormRef = ref<FormInstance>()
const emailForm = reactive({
  email: ''
})
const emailRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
}

// 验证码表单
const codeFormRef = ref<FormInstance>()
const codeForm = reactive({
  code: ''
})
const codeRules: FormRules = {
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' }
  ]
}

// 密码表单
const passwordFormRef = ref<FormInstance>()
const passwordForm = reactive({
  newPassword: '',
  confirmPassword: ''
})
const passwordRules: FormRules = {
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为6-20位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 加载状态
const sendingCode = ref(false)
const verifying = ref(false)
const resetting = ref(false)

// 发送验证码
const handleSendCode = async () => {
  const valid = await emailFormRef.value?.validate().catch(() => false)
  if (!valid) return

  sendingCode.value = true
  try {
    await sendVerificationCode({ email: emailForm.email })
    ElMessage.success('验证码已发送，请查收邮件')
    currentStep.value = 1
    startCountdown()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '发送失败')
  } finally {
    sendingCode.value = false
  }
}

// 开始倒计时
const startCountdown = () => {
  countdown.value = 60
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0 && timer) {
      clearInterval(timer)
      timer = null
    }
  }, 1000)
}

// 验证验证码
const handleVerifyCode = async () => {
  const valid = await codeFormRef.value?.validate().catch(() => false)
  if (!valid) return

  // 验证码格式正确后进入下一步
  currentStep.value = 2
}

// 重置密码
const handleResetPassword = async () => {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return

  resetting.value = true
  try {
    await resetPassword({
      email: emailForm.email,
      code: codeForm.code,
      new_password: passwordForm.newPassword
    })
    ElMessage.success('密码重置成功，请使用新密码登录')
    router.push('/login')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '重置失败')
  } finally {
    resetting.value = false
  }
}

// 返回登录
const goBack = () => {
  router.push('/login')
}

// 清理定时器
onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<style scoped lang="scss">
.forgot-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.forgot-password-container {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);

  .forgot-password-header {
    text-align: center;
    margin-bottom: 30px;

    h2 {
      margin: 0 0 8px 0;
      font-size: 24px;
      font-weight: 600;
      color: #303133;
    }

    p {
      margin: 0;
      font-size: 14px;
      color: #909399;
    }
  }

  .steps {
    margin-bottom: 30px;
  }

  .step-content {
    .email-display {
      text-align: center;
      padding: 16px;
      background: #f5f7fa;
      border-radius: 8px;
      margin-bottom: 20px;
      color: #606266;

      strong {
        color: #409eff;
      }
    }

    .resend-row {
      text-align: center;
      margin-top: 16px;
      font-size: 14px;
      color: #909399;
    }
  }

  .back-to-login {
    text-align: center;
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid #ebeef5;
  }
}
</style>
