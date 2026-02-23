<template>
  <div class="users-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>用户管理</h2>
      <p class="subtitle">管理系统用户账户，包括管理员、辅导员和学生账号</p>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="filters">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索用户名/学号/姓名"
          clearable
          style="width: 220px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="filters.role" placeholder="用户角色" clearable style="width: 140px" @change="handleSearch">
          <el-option label="管理员" value="admin" />
          <el-option label="辅导员" value="counselor" />
          <el-option label="学生" value="student" />
        </el-select>
        <el-select v-model="filters.is_active" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
          <el-option label="正常" :value="true" />
          <el-option label="禁用" :value="false" />
        </el-select>
      </div>
      <div class="actions">
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建用户
        </el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">
              {{ getRoleName(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联信息" min-width="160">
          <template #default="{ row }">
            <template v-if="row.role === 'student' && row.student">
              <span>{{ row.student.name }} ({{ row.student.class_name || '未分配班级' }})</span>
            </template>
            <template v-else-if="row.role === 'counselor'">
              <span class="text-muted">辅导员账号</span>
            </template>
            <template v-else>
              <span class="text-muted">-</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '正常' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="编辑" placement="top">
                <el-button link type="primary" class="action-btn" @click="handleEdit(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-dropdown trigger="click" @command="(cmd: string) => handleCommand(cmd, row)">
                <el-button link type="info" class="action-btn more-btn">
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="resetPassword">
                      <el-icon><Key /></el-icon>
                      <span>重置密码</span>
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-if="row.role !== 'admin'"
                      :command="row.is_active ? 'disable' : 'enable'"
                    >
                      <el-icon>
                        <CircleClose v-if="row.is_active" />
                        <CircleCheck v-else />
                      </el-icon>
                      <span>{{ row.is_active ? '禁用账号' : '启用账号' }}</span>
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-if="row.role !== 'admin'"
                      command="delete"
                      divided
                      class="delete-item"
                    >
                      <el-icon><Delete /></el-icon>
                      <span>删除账号</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :disabled="isEdit"
          />
        </el-form-item>

        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="用户角色" prop="role">
          <el-select v-model="form.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="辅导员" value="counselor" />
            <el-option label="学生" value="student" />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="form.role === 'student'"
          label="关联学生"
          prop="student_id"
        >
          <el-select
            v-model="form.student_id"
            placeholder="请选择关联的学生"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="student in studentOptions"
              :key="student.id"
              :label="`${student.name} (${student.student_no})`"
              :value="student.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item v-if="isEdit" label="状态">
          <el-switch
            v-model="form.is_active"
            active-text="正常"
            inactive-text="禁用"
            :disabled="form.role === 'admin'"
          />
          <span v-if="form.role === 'admin'" class="admin-hint">管理员账号无法被禁用</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog
      v-model="resetPasswordDialogVisible"
      title="重置密码"
      width="400px"
    >
      <el-form
        ref="resetPasswordFormRef"
        :model="resetPasswordForm"
        :rules="resetPasswordRules"
        label-width="100px"
      >
        <el-form-item label="用户名">
          <el-input :value="currentUser?.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="resetPasswordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="resetPasswordForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="resetPasswordDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="resettingPassword"
          @click="handleConfirmResetPassword"
        >
          确定重置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Edit, MoreFilled, Key, CircleClose, CircleCheck, Delete, Search } from '@element-plus/icons-vue'
import { getUsers, createUser, updateUser, deleteUser } from '@/api/user'
import { getStudents } from '@/api/student'
import type { User, UserRole, Student } from '@/types'

// 筛选条件
const filters = reactive({
  role: '',
  is_active: undefined as boolean | undefined
})

// 搜索关键词
const searchKeyword = ref('')

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 数据
const loading = ref(false)
const tableData = ref<User[]>([])
const studentOptions = ref<Student[]>([])

// 对话框
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const isEdit = ref(false)
const editId = ref<number | null>(null)

// 重置密码
const resetPasswordDialogVisible = ref(false)
const resettingPassword = ref(false)
const resetPasswordFormRef = ref<FormInstance>()
const currentUser = ref<User | null>(null)
const resetPasswordForm = reactive({
  newPassword: '',
  confirmPassword: ''
})

// 表单数据
const form = reactive({
  username: '',
  password: '',
  role: 'student' as UserRole,
  student_id: undefined as number | undefined,
  is_active: true
})

// 表单验证规则
const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在3到20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在6到20个字符', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择用户角色', trigger: 'change' }
  ],
  student_id: [
    {
      validator: (_rule, value, callback) => {
        if (form.role === 'student' && !value) {
          callback(new Error('请选择关联的学生'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

// 重置密码验证规则
const resetPasswordRules: FormRules = {
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在6到20个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== resetPasswordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 计算属性
const dialogTitle = computed(() => isEdit.value ? '编辑用户' : '新建用户')

// 获取角色名称
const getRoleName = (role: UserRole) => {
  const map: Record<UserRole, string> = {
    admin: '管理员',
    counselor: '辅导员',
    student: '学生'
  }
  return map[role] || role
}

// 获取角色标签类型
const getRoleTagType = (role: UserRole) => {
  const map: Record<UserRole, string> = {
    admin: 'danger',
    counselor: 'warning',
    student: 'success'
  }
  return map[role] || ''
}

// 获取数据
const fetchData = async () => {
  loading.value = true
  try {
    const res = await getUsers({
      page: pagination.page,
      page_size: pagination.pageSize,
      role: filters.role || undefined,
      is_active: filters.is_active,
      search: searchKeyword.value || undefined
    })
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('获取用户列表失败:', error)
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

// 获取学生列表（用于关联）
const fetchStudents = async () => {
  try {
    const res = await getStudents({ page: 1, page_size: 1000 })
    studentOptions.value = res.items || []
  } catch (error) {
    console.error('获取学生列表失败:', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

// 创建用户
const handleCreate = () => {
  isEdit.value = false
  editId.value = null
  resetFormData()
  dialogVisible.value = true
}

// 编辑用户
const handleEdit = (row: User) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    username: row.username,
    password: '',
    role: row.role,
    student_id: row.student_id,
    is_active: row.is_active
  })
  dialogVisible.value = true
}

// 删除用户
const handleDelete = async (row: User) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户「${row.username}」吗？删除后不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error(error?.response?.data?.detail || '删除失败')
    }
  }
}

// 切换用户状态
const handleToggleStatus = async (row: User) => {
  try {
    await updateUser(row.id, { is_active: !row.is_active })
    row.is_active = !row.is_active
    ElMessage.success(row.is_active ? '用户已启用' : '用户已禁用')
  } catch (error) {
    console.error('切换状态失败:', error)
    ElMessage.error('操作失败')
  }
}

// 下拉菜单命令处理
const handleCommand = async (command: string, row: User) => {
  switch (command) {
    case 'resetPassword':
      handleResetPassword(row)
      break
    case 'enable':
    case 'disable':
      handleToggleStatus(row)
      break
    case 'delete':
      handleDelete(row)
      break
  }
}

// 重置密码
const handleResetPassword = (row: User) => {
  currentUser.value = row
  resetPasswordForm.newPassword = ''
  resetPasswordForm.confirmPassword = ''
  resetPasswordDialogVisible.value = true
}

// 确认重置密码
const handleConfirmResetPassword = async () => {
  const valid = await resetPasswordFormRef.value?.validate().catch(() => false)
  if (!valid || !currentUser.value) return

  resettingPassword.value = true
  try {
    await updateUser(currentUser.value.id, {
      password: resetPasswordForm.newPassword
    })
    ElMessage.success('密码重置成功')
    resetPasswordDialogVisible.value = false
  } catch (error) {
    console.error('重置密码失败:', error)
    ElMessage.error('重置密码失败')
  } finally {
    resettingPassword.value = false
  }
}

// 重置表单数据
const resetFormData = () => {
  Object.assign(form, {
    username: '',
    password: '',
    role: 'student',
    student_id: undefined,
    is_active: true
  })
}

// 重置表单
const resetForm = () => {
  formRef.value?.resetFields()
  resetFormData()
}

// 提交表单
const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value && editId.value) {
      const data: any = {
        is_active: form.is_active
      }
      if (form.password) {
        data.password = form.password
      }
      await updateUser(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createUser({
        username: form.username,
        password: form.password,
        role: form.role,
        student_id: form.student_id
      })
      ElMessage.success('创建成功')
    }

    dialogVisible.value = false
    fetchData()
  } catch (error: any) {
    console.error('保存失败:', error)
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchData()
  fetchStudents()
})
</script>

<style scoped lang="scss">
.users-container {
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

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .filters {
      display: flex;
      gap: 12px;
    }

    .actions {
      display: flex;
      gap: 12px;
    }
  }

  .table-card {
    .text-muted {
      color: var(--el-text-color-placeholder);
    }
  }

  // 操作按钮样式
  .action-buttons {
    display: inline-flex;
    align-items: center;
    gap: 4px;

    .action-btn {
      width: 32px;
      height: 32px;
      padding: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      transition: all 0.2s ease;

      .el-icon {
        font-size: 16px;
      }

      &:hover {
        background-color: var(--el-fill-color-light);
      }
    }

    .more-btn {
      .el-icon {
        font-size: 14px;
      }
    }
  }

  .admin-hint {
    margin-left: 12px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    padding: 16px 0 0;
  }
}

// 下拉菜单删除项样式（全局）
:deep(.delete-item) {
  color: var(--el-color-danger);

  .el-icon {
    color: var(--el-color-danger);
  }

  &:hover {
    background-color: var(--el-color-danger-light-9);
    color: var(--el-color-danger);
  }
}
</style>
