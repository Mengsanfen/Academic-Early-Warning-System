<template>
  <div class="profile-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>个人信息</h2>
      <p class="subtitle">查看和管理您的个人信息</p>
    </div>

    <div class="profile-content" v-loading="loading">
      <el-row :gutter="24">
        <!-- 左侧：头像和基本信息卡片 -->
        <el-col :span="8">
          <el-card class="profile-card">
            <div class="avatar-section">
              <div class="avatar-wrapper" @click="triggerAvatarUpload">
                <el-avatar :size="120" :src="avatarFullUrl" class="user-avatar">
                  <el-icon :size="50"><User /></el-icon>
                </el-avatar>
                <div class="avatar-overlay">
                  <el-icon><Camera /></el-icon>
                  <span>更换头像</span>
                </div>
              </div>
              <input
                ref="avatarInput"
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                style="display: none"
                @change="handleAvatarChange"
              />
              <h3 class="user-name">{{ profile?.nickname || profile?.username || '用户' }}</h3>
              <p class="user-role">
                <el-tag :type="getRoleTagType(profile?.role)" size="small">
                  {{ getRoleName(profile?.role) }}
                </el-tag>
              </p>
            </div>

            <el-divider />

            <div class="quick-info">
              <div class="info-item">
                <el-icon><User /></el-icon>
                <span>账号：{{ profile?.username }}</span>
              </div>
              <div class="info-item" v-if="profile?.student_no">
                <el-icon><Postcard /></el-icon>
                <span>学号：{{ profile?.student_no }}</span>
              </div>
              <div class="info-item" v-if="profile?.class_name">
                <el-icon><School /></el-icon>
                <span>班级：{{ profile?.class_name }}</span>
              </div>
              <div class="info-item">
                <el-icon><Calendar /></el-icon>
                <span>注册：{{ formatDate(profile?.created_at) }}</span>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：详细信息编辑 -->
        <el-col :span="16">
          <el-card class="info-card">
            <template #header>
              <div class="card-header">
                <span>基本信息</span>
                <el-button
                  v-if="!isEditing"
                  type="primary"
                  text
                  @click="startEdit"
                >
                  <el-icon><Edit /></el-icon>
                  编辑资料
                </el-button>
                <template v-else>
                  <el-button @click="cancelEdit">取消</el-button>
                  <el-button type="primary" :loading="saving" @click="saveProfile">
                    保存
                  </el-button>
                </template>
              </div>
            </template>

            <el-form
              ref="formRef"
              :model="editForm"
              :rules="formRules"
              label-width="100px"
              :disabled="!isEditing"
            >
              <el-form-item label="用户名">
                <el-input :model-value="profile?.username || ''" disabled />
              </el-form-item>

              <el-form-item label="昵称" prop="nickname">
                <el-input
                  v-model="editForm.nickname"
                  placeholder="请输入昵称"
                  maxlength="20"
                  show-word-limit
                />
              </el-form-item>

              <el-form-item label="邮箱" prop="email">
                <el-input
                  v-model="editForm.email"
                  placeholder="请输入邮箱"
                  type="email"
                />
              </el-form-item>

              <el-form-item label="手机号" prop="phone">
                <el-input
                  v-model="editForm.phone"
                  placeholder="请输入手机号"
                  maxlength="11"
                />
              </el-form-item>

              <el-form-item label="个人简介" prop="bio">
                <el-input
                  v-model="editForm.bio"
                  type="textarea"
                  :rows="4"
                  placeholder="介绍一下自己..."
                  maxlength="200"
                  show-word-limit
                />
              </el-form-item>
            </el-form>
          </el-card>

          <!-- 安全设置 -->
          <el-card class="security-card">
            <template #header>
              <div class="card-header">
                <span>安全设置</span>
              </div>
            </template>

            <div class="security-item">
              <div class="security-info">
                <el-icon :size="20"><Lock /></el-icon>
                <div>
                  <h4>登录密码</h4>
                  <p>定期更换密码可以提高账号安全性</p>
                </div>
              </div>
              <el-button type="primary" text @click="showPasswordDialog = true">
                修改密码
              </el-button>
            </div>

            <el-divider />

            <div class="security-item">
              <div class="security-info">
                <el-icon :size="20"><CircleCheck /></el-icon>
                <div>
                  <h4>账号状态</h4>
                  <p>
                    <el-tag :type="profile?.is_active ? 'success' : 'danger'" size="small">
                      {{ profile?.is_active ? '正常' : '已禁用' }}
                    </el-tag>
                    <el-tag v-if="profile?.first_login" type="warning" size="small" style="margin-left: 8px">
                      首次登录
                    </el-tag>
                  </p>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="showPasswordDialog"
      title="修改密码"
      width="450px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="100px"
      >
        <el-form-item
          v-if="!profile?.first_login"
          label="原密码"
          prop="old_password"
        >
          <el-input
            v-model="passwordForm.old_password"
            type="password"
            placeholder="请输入原密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="passwordForm.confirm_password"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" :loading="changingPassword" @click="handleChangePassword">
          确定修改
        </el-button>
      </template>
    </el-dialog>

    <!-- 头像裁剪对话框（简化版，直接上传） -->
    <el-dialog
      v-model="showAvatarDialog"
      title="更换头像"
      width="400px"
    >
      <div class="avatar-preview">
        <el-avatar :size="200" :src="previewAvatar" />
      </div>
      <template #footer>
        <el-button @click="showAvatarDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploadingAvatar" @click="uploadAvatar">
          确认上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules, type UploadProps } from 'element-plus'
import { User, Camera, Edit, Lock, CircleCheck, Postcard, School, Calendar } from '@element-plus/icons-vue'
import { getUserProfile, updateProfile, uploadAvatar as uploadAvatarApi, changePassword } from '@/api/auth'
import type { UserProfile, UserProfileUpdate, UserRole } from '@/types'

// 数据
const loading = ref(false)
const saving = ref(false)
const uploadingAvatar = ref(false)
const changingPassword = ref(false)
const isEditing = ref(false)
const profile = ref<UserProfile | null>(null)

// 编辑表单
const formRef = ref<FormInstance>()
const editForm = reactive({
  nickname: '',
  email: '',
  phone: '',
  bio: ''
})

// 表单验证规则
const formRules: FormRules = {
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ]
}

// 修改密码
const showPasswordDialog = ref(false)
const passwordFormRef = ref<FormInstance>()
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules: FormRules = {
  old_password: [
    { required: true, message: '请输入原密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

// 头像上传
const avatarInput = ref<HTMLInputElement>()
const showAvatarDialog = ref(false)
const previewAvatar = ref('')
const selectedFile = ref<File | null>(null)

// 计算属性：头像完整URL
const avatarFullUrl = computed(() => {
  if (profile.value?.avatar_url) {
    // 如果是相对路径，添加API基础URL
    if (profile.value.avatar_url.startsWith('/')) {
      return `http://localhost:8000${profile.value.avatar_url}`
    }
    return profile.value.avatar_url
  }
  return ''
})

// 获取用户信息
async function fetchProfile() {
  loading.value = true
  try {
    profile.value = await getUserProfile()
    // 同步到编辑表单
    editForm.nickname = profile.value.nickname || ''
    editForm.email = profile.value.email || ''
    editForm.phone = profile.value.phone || ''
    editForm.bio = profile.value.bio || ''
  } catch (error) {
    console.error('获取用户信息失败', error)
  } finally {
    loading.value = false
  }
}

// 开始编辑
function startEdit() {
  isEditing.value = true
  editForm.nickname = profile.value?.nickname || ''
  editForm.email = profile.value?.email || ''
  editForm.phone = profile.value?.phone || ''
  editForm.bio = profile.value?.bio || ''
}

// 取消编辑
function cancelEdit() {
  isEditing.value = false
  formRef.value?.resetFields()
}

// 保存个人信息
async function saveProfile() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const updateData: UserProfileUpdate = {}
    if (editForm.nickname !== profile.value?.nickname) {
      updateData.nickname = editForm.nickname
    }
    if (editForm.email !== profile.value?.email) {
      updateData.email = editForm.email
    }
    if (editForm.phone !== profile.value?.phone) {
      updateData.phone = editForm.phone
    }
    if (editForm.bio !== profile.value?.bio) {
      updateData.bio = editForm.bio
    }

    if (Object.keys(updateData).length > 0) {
      profile.value = await updateProfile(updateData)
      ElMessage.success('保存成功')
    }
    isEditing.value = false
  } catch (error) {
    console.error('保存失败', error)
  } finally {
    saving.value = false
  }
}

// 触发头像上传
function triggerAvatarUpload() {
  avatarInput.value?.click()
}

// 头像文件选择
function handleAvatarChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  // 验证文件类型
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('只支持 JPG、PNG、GIF、WebP 格式的图片')
    return
  }

  // 验证文件大小
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 2MB')
    return
  }

  // 预览图片
  const reader = new FileReader()
  reader.onload = (e) => {
    previewAvatar.value = e.target?.result as string
    selectedFile.value = file
    showAvatarDialog.value = true
  }
  reader.readAsDataURL(file)

  // 重置input
  target.value = ''
}

// 上传头像
async function uploadAvatar() {
  if (!selectedFile.value) return

  uploadingAvatar.value = true
  try {
    const res = await uploadAvatarApi(selectedFile.value)
    profile.value = {
      ...profile.value!,
      avatar_url: res.avatar_url
    }
    showAvatarDialog.value = false
    ElMessage.success('头像更新成功')
  } catch (error) {
    console.error('上传头像失败', error)
  } finally {
    uploadingAvatar.value = false
  }
}

// 修改密码
async function handleChangePassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return

  changingPassword.value = true
  try {
    await changePassword({
      old_password: profile.value?.first_login ? undefined : passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    ElMessage.success('密码修改成功')
    showPasswordDialog.value = false
    // 重置表单
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    // 刷新用户信息
    await fetchProfile()
  } catch (error) {
    console.error('修改密码失败', error)
  } finally {
    changingPassword.value = false
  }
}

// 获取角色名称
function getRoleName(role?: UserRole) {
  const map: Record<string, string> = {
    admin: '管理员',
    counselor: '辅导员',
    student: '学生'
  }
  return map[role || ''] || '未知'
}

// 获取角色标签类型
function getRoleTagType(role?: UserRole) {
  const map: Record<string, string> = {
    admin: 'danger',
    counselor: 'warning',
    student: 'primary'
  }
  return map[role || ''] || ''
}

// 格式化日期
function formatDate(date?: string) {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

onMounted(() => {
  fetchProfile()
})
</script>

<style scoped lang="scss">
.profile-container {
  padding: 20px;

  .page-header {
    margin-bottom: 20px;

    h2 {
      margin: 0 0 8px 0;
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }

    .subtitle {
      margin: 0;
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }
}

.profile-card {
  .avatar-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px 0;

    .avatar-wrapper {
      position: relative;
      cursor: pointer;

      &:hover .avatar-overlay {
        opacity: 1;
      }

      .user-avatar {
        border: 4px solid var(--el-border-color-lighter);
        background: var(--el-fill-color-light);
      }

      .avatar-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        border-radius: 50%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: white;
        opacity: 0;
        transition: opacity 0.3s;

        .el-icon {
          font-size: 24px;
          margin-bottom: 4px;
        }

        span {
          font-size: 12px;
        }
      }
    }

    .user-name {
      margin: 16px 0 8px;
      font-size: 20px;
      font-weight: 600;
    }

    .user-role {
      margin: 0;
    }
  }

  .quick-info {
    .info-item {
      display: flex;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid var(--el-border-color-lighter);

      &:last-child {
        border-bottom: none;
      }

      .el-icon {
        margin-right: 12px;
        color: var(--el-text-color-secondary);
        font-size: 18px;
      }

      span {
        color: var(--el-text-color-regular);
      }
    }
  }
}

.info-card,
.security-card {
  margin-bottom: 20px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }
}

.security-card {
  .security-item {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .security-info {
      display: flex;
      align-items: center;
      gap: 16px;

      .el-icon {
        color: var(--el-color-primary);
      }

      h4 {
        margin: 0 0 4px;
        font-size: 14px;
        font-weight: 500;
      }

      p {
        margin: 0;
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
  }
}

.avatar-preview {
  display: flex;
  justify-content: center;
  padding: 20px;
}
</style>
