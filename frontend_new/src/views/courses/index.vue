<template>
  <div class="courses-container">
    <div class="page-header">
      <div>
        <h2>课程管理</h2>
        <p class="subtitle">统一维护课程学分、授课班级和课程类型，为必修课、选修课等差异化规则提供基础数据。</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建课程
        </el-button>
        <el-button :disabled="selectedCourses.length === 0" @click="handleBatchUpdateType">
          <el-icon><Edit /></el-icon>
          批量调整类型
        </el-button>
      </div>
    </div>

    <el-row :gutter="16" class="stats-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-primary" shadow="hover">
          <div class="stat-value">{{ statistics.total }}</div>
          <div class="stat-label">课程总数</div>
        </el-card>
      </el-col>
      <el-col
        v-for="item in statistics.by_type.slice(0, 3)"
        :key="item.type"
        :xs="24"
        :sm="12"
        :lg="6"
      >
        <el-card class="stat-card" shadow="hover">
          <div class="stat-value">{{ item.count }}</div>
          <div class="stat-label">{{ item.type_name }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="panel-card" shadow="never">
      <div class="toolbar">
        <div class="filters">
          <el-input
            v-model="filters.course_name"
            placeholder="搜索课程名称"
            clearable
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select v-model="filters.semester" clearable placeholder="学期">
            <el-option v-for="item in semesterOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select v-model="filters.course_type" clearable placeholder="课程类型">
            <el-option
              v-for="item in courseTypeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
          <el-select v-model="filters.class_id" clearable filterable placeholder="授课班级">
            <el-option
              v-for="item in classOptions"
              :key="item.id"
              :label="formatClassLabel(item)"
              :value="item.id"
            />
          </el-select>
        </div>
        <div class="toolbar-actions">
          <el-button @click="handleReset">重置</el-button>
          <el-button type="primary" @click="handleSearch">查询</el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        border
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="course_code" label="课程代码" width="130" />
        <el-table-column prop="course_name" label="课程名称" min-width="180" />
        <el-table-column prop="credit" label="学分" width="90" align="center" />
        <el-table-column prop="semester" label="学期" width="150" />
        <el-table-column label="课程类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getCourseTypeTagType(row.course_type)">
              {{ row.course_type_name || getCourseTypeName(row.course_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="teacher_name" label="授课教师" width="120" />
        <el-table-column label="授课班级" min-width="180">
          <template #default="{ row }">
            <div class="class-cell">
              <span>{{ row.class_name || '未设置' }}</span>
              <span v-if="row.grade" class="class-meta">{{ row.grade }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
              <el-popconfirm title="确定删除这门课程吗？" @confirm="handleDelete(row)">
                <template #reference>
                  <el-button link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
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
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="680px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="课程代码" prop="course_code">
              <el-input v-model="form.course_code" :disabled="isEdit" placeholder="例如 CS101" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="课程名称" prop="course_name">
              <el-input v-model="form.course_name" placeholder="请输入课程名称" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="学分" prop="credit">
              <el-input-number v-model="form.credit" :min="0.5" :max="10" :step="0.5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="学期" prop="semester">
              <el-input v-model="form.semester" placeholder="例如 2025-2026-1" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="课程类型" prop="course_type">
              <el-select v-model="form.course_type" placeholder="请选择课程类型" style="width: 100%">
                <el-option
                  v-for="item in courseTypeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="授课教师" prop="teacher_name">
              <el-input v-model="form.teacher_name" placeholder="请输入授课教师姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="授课班级" prop="class_id">
              <el-select v-model="form.class_id" clearable filterable placeholder="请选择授课班级" style="width: 100%">
                <el-option
                  v-for="item in classOptions"
                  :key="item.id"
                  :label="formatClassLabel(item)"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="课程类型会直接参与规则执行，例如：必修学分不足、选修学分不足、必修课挂科数过多。"
        />
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" title="批量调整课程类型" width="420px">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        :title="`已选择 ${selectedCourses.length} 门课程，调整后规则执行会立即按新类型生效。`"
      />
      <el-form label-width="96px" style="margin-top: 16px">
        <el-form-item label="调整为">
          <el-select v-model="batchCourseType" placeholder="请选择课程类型" style="width: 100%">
            <el-option
              v-for="item in courseTypeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchSubmitting" @click="submitBatchUpdate">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Edit, Plus, Search } from '@element-plus/icons-vue'
import { getClasses, type ClassOption } from '@/api/class'
import {
  batchUpdateCourseType,
  createCourse,
  deleteCourse,
  getCourseStatistics,
  getCourseTypes,
  getCourses,
  getSemesters,
  updateCourse
} from '@/api/course'
import type { Course, CourseType } from '@/types'

interface CourseTypeOption {
  value: CourseType
  label: string
  description?: string
}

const filters = reactive({
  course_name: '',
  semester: '',
  course_type: '' as CourseType | '',
  class_id: null as number | null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const loading = ref(false)
const tableData = ref<Course[]>([])
const semesterOptions = ref<string[]>([])
const courseTypeOptions = ref<CourseTypeOption[]>([])
const classOptions = ref<ClassOption[]>([])
const selectedCourses = ref<Course[]>([])
const statistics = ref({
  total: 0,
  by_type: [] as Array<{ type: string; type_name: string; count: number }>,
  by_semester: [] as Array<{ semester: string; count: number }>
})

const dialogVisible = ref(false)
const batchDialogVisible = ref(false)
const submitting = ref(false)
const batchSubmitting = ref(false)
const batchCourseType = ref<CourseType | ''>('')
const formRef = ref<FormInstance>()
const isEdit = ref(false)
const editId = ref<number | null>(null)

const form = reactive({
  course_code: '',
  course_name: '',
  credit: 2,
  semester: '',
  teacher_name: '',
  class_id: null as number | null,
  course_type: 'required' as CourseType
})

const rules: FormRules = {
  course_code: [{ required: true, message: '请输入课程代码', trigger: 'blur' }],
  course_name: [{ required: true, message: '请输入课程名称', trigger: 'blur' }],
  credit: [{ required: true, message: '请输入学分', trigger: 'change' }],
  semester: [{ required: true, message: '请输入学期', trigger: 'blur' }],
  course_type: [{ required: true, message: '请选择课程类型', trigger: 'change' }]
}

const dialogTitle = computed(() => (isEdit.value ? '编辑课程' : '新建课程'))

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getCourses({
      page: pagination.page,
      page_size: pagination.pageSize,
      course_name: filters.course_name || undefined,
      semester: filters.semester || undefined,
      course_type: filters.course_type || undefined,
      class_id: filters.class_id || undefined
    })
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('获取课程列表失败', error)
    ElMessage.error('获取课程列表失败')
  } finally {
    loading.value = false
  }
}

const fetchSemesters = async () => {
  try {
    const res = await getSemesters()
    semesterOptions.value = res.items || []
  } catch (error) {
    console.error('获取学期列表失败', error)
  }
}

const fetchCourseTypes = async () => {
  try {
    const res = await getCourseTypes()
    courseTypeOptions.value = (res.items || []) as CourseTypeOption[]
  } catch (error) {
    console.error('获取课程类型失败', error)
  }
}

const fetchClasses = async () => {
  try {
    const res = await getClasses()
    classOptions.value = res.items || []
  } catch (error) {
    console.error('获取班级列表失败', error)
  }
}

const fetchStatistics = async () => {
  try {
    const res = await getCourseStatistics()
    statistics.value = res
  } catch (error) {
    console.error('获取课程统计失败', error)
  }
}

const formatClassLabel = (item: ClassOption) => {
  if (item.department_name) {
    return `${item.grade} ${item.name} · ${item.department_name}`
  }
  return `${item.grade} ${item.name}`
}

const getCourseTypeName = (type: CourseType) => {
  const target = courseTypeOptions.value.find(item => item.value === type)
  return target?.label || type
}

const getCourseTypeTagType = (type: CourseType): 'success' | 'warning' | 'info' | 'danger' | undefined => {
  const map: Record<CourseType, 'success' | 'warning' | 'info' | 'danger' | undefined> = {
    required: 'danger',
    elective: 'success',
    public: 'info',
    professional: 'warning',
    practice: undefined,
  }
  return map[type]
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  filters.course_name = ''
  filters.semester = ''
  filters.course_type = ''
  filters.class_id = null
  handleSearch()
}

const handleSelectionChange = (selection: Course[]) => {
  selectedCourses.value = selection
}

const handleCreate = () => {
  isEdit.value = false
  editId.value = null
  resetFormData()
  dialogVisible.value = true
}

const handleEdit = (row: Course) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    course_code: row.course_code,
    course_name: row.course_name,
    credit: row.credit,
    semester: row.semester,
    teacher_name: row.teacher_name || '',
    class_id: row.class_id ?? null,
    course_type: row.course_type
  })
  dialogVisible.value = true
}

const handleDelete = async (row: Course) => {
  try {
    await deleteCourse(row.id)
    ElMessage.success('删除成功')
    fetchData()
    fetchStatistics()
  } catch (error: any) {
    console.error('删除课程失败', error)
    ElMessage.error(error?.response?.data?.detail || '删除课程失败')
  }
}

const handleBatchUpdateType = () => {
  batchCourseType.value = ''
  batchDialogVisible.value = true
}

const submitBatchUpdate = async () => {
  if (!batchCourseType.value) {
    ElMessage.warning('请选择课程类型')
    return
  }

  batchSubmitting.value = true
  try {
    const res = await batchUpdateCourseType(
      selectedCourses.value.map(item => item.id),
      batchCourseType.value as CourseType
    )
    ElMessage.success(res.message || '批量修改成功')
    batchDialogVisible.value = false
    selectedCourses.value = []
    fetchData()
    fetchStatistics()
  } catch (error: any) {
    console.error('批量修改课程类型失败', error)
    ElMessage.error(error?.response?.data?.detail || '批量修改课程类型失败')
  } finally {
    batchSubmitting.value = false
  }
}

const resetFormData = () => {
  Object.assign(form, {
    course_code: '',
    course_name: '',
    credit: 2,
    semester: '',
    teacher_name: '',
    class_id: null,
    course_type: 'required'
  })
}

const resetForm = () => {
  formRef.value?.resetFields()
  resetFormData()
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = {
      course_code: form.course_code,
      course_name: form.course_name,
      credit: form.credit,
      semester: form.semester,
      teacher_name: form.teacher_name || undefined,
      class_id: form.class_id ?? undefined,
      course_type: form.course_type
    }

    if (isEdit.value && editId.value) {
      await updateCourse(editId.value, payload)
      ElMessage.success('课程更新成功')
    } else {
      await createCourse(payload)
      ElMessage.success('课程创建成功')
    }

    dialogVisible.value = false
    fetchData()
    fetchSemesters()
    fetchStatistics()
  } catch (error: any) {
    console.error('保存课程失败', error)
    ElMessage.error(error?.response?.data?.detail || '保存课程失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchData()
  fetchSemesters()
  fetchCourseTypes()
  fetchClasses()
  fetchStatistics()
})
</script>

<style scoped lang="scss">
.courses-container {
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
    font-size: 32px;
    font-weight: 700;
    color: #1f2937;
  }

  .subtitle {
    margin: 0;
    color: #64748b;
    line-height: 1.6;
  }
}

.header-actions {
  display: flex;
  gap: 12px;
}

.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  border-radius: 18px;

  :deep(.el-card__body) {
    padding: 22px;
  }
}

.stat-primary {
  background: linear-gradient(135deg, #1d4ed8, #3b82f6);
  color: #fff;
}

.stat-value {
  font-size: 30px;
  font-weight: 700;
}

.stat-label {
  margin-top: 8px;
  font-size: 14px;
  color: inherit;
  opacity: 0.88;
}

.panel-card {
  border-radius: 18px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filters {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 12px;
  flex: 1;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
}

.class-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.class-meta {
  font-size: 12px;
  color: #94a3b8;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 1200px) {
  .filters {
    grid-template-columns: repeat(2, minmax(160px, 1fr));
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }

  .header-actions,
  .toolbar-actions {
    width: 100%;
  }

  .header-actions :deep(.el-button),
  .toolbar-actions :deep(.el-button) {
    flex: 1;
  }

  .filters {
    grid-template-columns: 1fr;
  }
}
</style>

