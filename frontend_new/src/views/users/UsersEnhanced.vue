<template>
  <div class="users-container">
    <div class="page-header">
      <div>
        <h2>用户管理</h2>
        <p class="subtitle">管理员可创建账号，并为辅导员分配可管理的班级范围。</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        新建用户
      </el-button>
    </div>

    <div class="toolbar">
      <div class="filters">
        <el-input
          v-model="filters.search"
          placeholder="搜索用户名/学号/姓名"
          clearable
          style="width: 240px"
          @keyup.enter="fetchUsers"
          @clear="fetchUsers"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="filters.role" placeholder="角色" clearable style="width: 140px" @change="handleSearch">
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
        <el-button @click="handleResetFilters">重置</el-button>
        <el-button @click="fetchUsers">刷新</el-button>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="users" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="160" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">
              {{ getRoleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联信息" min-width="180">
          <template #default="{ row }">
            <template v-if="row.role === 'student' && row.student">
              {{ row.student.name }}（{{ row.student.student_no }}）
            </template>
            <template v-else-if="row.role === 'counselor'">
              <span class="text-muted">辅导员账号</span>
            </template>
            <template v-else>
              <span class="text-muted">系统管理员</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="管理班级" min-width="220">
          <template #default="{ row }">
            <template v-if="row.role === 'counselor'">
              <div v-if="row.managed_class_names.length" class="class-tags">
                <el-tag
                  v-for="className in row.managed_class_names"
                  :key="className"
                  size="small"
                  type="info"
                >
                  {{ className }}
                </el-tag>
              </div>
              <span v-else class="text-muted">未分配班级</span>
            </template>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
            <el-button v-if="row.role === 'counselor'" type="warning" link @click="openClassDialog(row)">班级权限</el-button>
            <el-button v-if="row.role !== 'admin'" :type="row.is_active ? 'warning' : 'success'" link @click="toggleStatus(row)">
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button v-if="row.role !== 'admin'" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchUsers"
          @current-change="fetchUsers"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingUser ? '编辑用户' : '新建用户'"
      width="560px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="96px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="Boolean(editingUser)" />
        </el-form-item>

        <el-form-item :label="editingUser ? '重置密码' : '密码'" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editingUser ? '留空则不修改密码' : '请输入密码'"
          />
        </el-form-item>

        <el-form-item label="用户角色" prop="role">
          <el-select v-model="form.role" :disabled="Boolean(editingUser)" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="辅导员" value="counselor" />
            <el-option label="学生" value="student" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="form.role === 'student'" label="关联学生" prop="student_id">
          <el-select
            v-model="form.student_id"
            filterable
            placeholder="请选择学生"
            style="width: 100%"
            :disabled="Boolean(editingUser)"
          >
            <el-option
              v-for="student in studentOptions"
              :key="student.id"
              :label="`${student.name}（${student.student_no}）`"
              :value="student.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item v-if="form.role === 'counselor'" label="管理班级">
          <el-select
            v-model="form.managed_class_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择可管理班级"
            style="width: 100%"
          >
            <el-option
              v-for="classItem in classOptions"
              :key="classItem.id"
              :label="`${classItem.grade}级 ${classItem.name}`"
              :value="classItem.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item v-if="editingUser" label="账号状态">
          <el-switch
            v-model="form.is_active"
            active-text="正常"
            inactive-text="禁用"
            :disabled="form.role === 'admin'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="classDialogVisible"
      title="配置辅导员管理班级"
      width="560px"
      :close-on-click-modal="false"
    >
      <template v-if="classEditingUser">
        <div class="class-dialog-header">
          <div class="class-dialog-title">{{ classEditingUser.username }}</div>
          <div class="class-dialog-subtitle">为该辅导员分配可查看和可管理的班级范围。</div>
        </div>
        <el-select
          v-model="classForm.managed_class_ids"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          placeholder="请选择班级"
          style="width: 100%"
        >
          <el-option
            v-for="classItem in classOptions"
            :key="classItem.id"
            :label="`${classItem.grade}级 ${classItem.name}`"
            :value="classItem.id"
          />
        </el-select>
      </template>
      <template #footer>
        <el-button @click="classDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="classSubmitting" @click="submitCounselorClasses">保存权限</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'

import { getStudents } from '@/api/student'
import { request } from '@/utils/request'
import type { UserRole } from '@/types'

type TagType = 'success' | 'warning' | 'primary' | 'info' | 'danger'

type StudentOption = {
  id: number
  student_no: string
  name: string
}

type ClassOption = {
  id: number
  name: string
  grade: string
}

type UserRow = {
  id: number
  username: string
  role: UserRole
  student_id?: number
  is_active: boolean
  managed_class_ids: string | null
  managed_class_ids_list: number[]
  managed_class_names: string[]
  student?: {
    id: number
    student_no: string
    name: string
    class_name?: string
  } | null
}

const loading = ref(false)
const submitting = ref(false)
const classSubmitting = ref(false)
const dialogVisible = ref(false)
const classDialogVisible = ref(false)
const editingUser = ref<UserRow | null>(null)
const classEditingUser = ref<UserRow | null>(null)
const formRef = ref<FormInstance>()

const users = ref<UserRow[]>([])
const studentOptions = ref<StudentOption[]>([])
const classOptions = ref<ClassOption[]>([])

const filters = reactive({
  search: '',
  role: '' as '' | UserRole,
  is_active: undefined as boolean | undefined
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const form = reactive({
  username: '',
  password: '',
  role: 'student' as UserRole,
  student_id: undefined as number | undefined,
  managed_class_ids: [] as number[],
  is_active: true
})

const classForm = reactive({
  managed_class_ids: [] as number[]
})

const roleTextMap: Record<UserRole, string> = {
  admin: '管理员',
  counselor: '辅导员',
  student: '学生'
}

const roleTagMap: Record<UserRole, TagType> = {
  admin: 'danger',
  counselor: 'warning',
  student: 'success'
}

function getRoleText(role: UserRole) {
  return roleTextMap[role]
}

function getRoleTagType(role: UserRole) {
  return roleTagMap[role]
}

const formRules = computed<FormRules>(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度需在 3-20 个字符之间', trigger: 'blur' }
  ],
  password: editingUser.value
    ? [{ min: 6, max: 20, message: '密码长度需在 6-20 个字符之间', trigger: 'blur' }]
    : [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, max: 20, message: '密码长度需在 6-20 个字符之间', trigger: 'blur' }
      ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  student_id: [
    {
      validator: (_rule, value, callback) => {
        if (form.role === 'student' && !value) {
          callback(new Error('学生账号必须关联学生'))
          return
        }
        callback()
      },
      trigger: 'change'
    }
  ]
}))

function resetForm() {
  formRef.value?.resetFields()
  editingUser.value = null
  form.username = ''
  form.password = ''
  form.role = 'student'
  form.student_id = undefined
  form.managed_class_ids = []
  form.is_active = true
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row: UserRow) {
  editingUser.value = row
  form.username = row.username
  form.password = ''
  form.role = row.role
  form.student_id = row.student_id
  form.managed_class_ids = [...row.managed_class_ids_list]
  form.is_active = row.is_active
  dialogVisible.value = true
}

function openClassDialog(row: UserRow) {
  classEditingUser.value = row
  classForm.managed_class_ids = [...row.managed_class_ids_list]
  classDialogVisible.value = true
}

function handleSearch() {
  pagination.page = 1
  fetchUsers()
}

function handleResetFilters() {
  filters.search = ''
  filters.role = ''
  filters.is_active = undefined
  pagination.page = 1
  fetchUsers()
}

async function fetchUsers() {
  loading.value = true
  try {
    const response = await request.get<{
      items: UserRow[]
      total: number
      page: number
      page_size: number
    }>('/users', {
      params: {
        page: pagination.page,
        page_size: pagination.pageSize,
        search: filters.search || undefined,
        role: filters.role || undefined,
        is_active: filters.is_active
      }
    })
    users.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    console.error('加载用户列表失败', error)
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchStudents() {
  try {
    const response = await getStudents({ page: 1, page_size: 1000 })
    studentOptions.value = response.items || []
  } catch (error) {
    console.error('加载学生选项失败', error)
  }
}

async function fetchClassOptions() {
  try {
    const response = await request.get<{ items: ClassOption[] }>('/users/class-options')
    classOptions.value = response.items || []
  } catch (error) {
    console.error('加载班级选项失败', error)
    ElMessage.error('加载班级选项失败')
  }
}

async function submitForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editingUser.value) {
      await request.put(`/users/${editingUser.value.id}`, {
        password: form.password || undefined,
        is_active: form.is_active,
        managed_class_ids: form.role === 'counselor' ? form.managed_class_ids : undefined
      })
      ElMessage.success('用户更新成功')
    } else {
      await request.post('/users', {
        username: form.username,
        password: form.password,
        role: form.role,
        student_id: form.role === 'student' ? form.student_id : undefined,
        managed_class_ids: form.role === 'counselor' ? form.managed_class_ids : []
      })
      ElMessage.success('用户创建成功')
    }

    dialogVisible.value = false
    fetchUsers()
  } catch (error: any) {
    console.error('保存用户失败', error)
    ElMessage.error(error?.response?.data?.detail || '保存用户失败')
  } finally {
    submitting.value = false
  }
}

async function submitCounselorClasses() {
  if (!classEditingUser.value) return

  classSubmitting.value = true
  try {
    await request.put(`/users/counselors/${classEditingUser.value.id}/classes`, {
      managed_class_ids: classForm.managed_class_ids
    })
    ElMessage.success('辅导员权限更新成功')
    classDialogVisible.value = false
    fetchUsers()
  } catch (error: any) {
    console.error('更新辅导员权限失败', error)
    ElMessage.error(error?.response?.data?.detail || '更新辅导员权限失败')
  } finally {
    classSubmitting.value = false
  }
}

async function toggleStatus(row: UserRow) {
  try {
    await request.put(`/users/${row.id}`, {
      is_active: !row.is_active
    })
    ElMessage.success(!row.is_active ? '用户已启用' : '用户已禁用')
    fetchUsers()
  } catch (error: any) {
    console.error('更新状态失败', error)
    ElMessage.error(error?.response?.data?.detail || '更新状态失败')
  }
}

async function handleDelete(row: UserRow) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户“${row.username}”吗？删除后无法恢复。`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )
    await request.delete(`/users/${row.id}`)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除用户失败', error)
      ElMessage.error(error?.response?.data?.detail || '删除用户失败')
    }
  }
}

onMounted(() => {
  fetchUsers()
  fetchStudents()
  fetchClassOptions()
})
</script>

<style scoped lang="scss">
.users-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;

  h2 {
    margin: 0 0 8px;
    font-size: 24px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .subtitle {
    margin: 0;
    color: var(--el-text-color-secondary);
    font-size: 14px;
  }
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;

  .filters,
  .actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
}

.table-card {
  .text-muted {
    color: var(--el-text-color-placeholder);
  }
}

.class-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.class-dialog-header {
  margin-bottom: 16px;

  .class-dialog-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 6px;
  }

  .class-dialog-subtitle {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}

@media (max-width: 900px) {
  .page-header,
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
