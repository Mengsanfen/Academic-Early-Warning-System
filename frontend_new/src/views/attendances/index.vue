<template>
  <div class="attendance-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>考勤管理</h2>
      <div class="header-actions">
        <el-button @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>
          批量导入
        </el-button>
        <el-button type="primary" @click="openDialog()">
          <el-icon><Plus /></el-icon>
          录入考勤
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card present">
          <div class="stat-content">
            <div class="stat-value">{{ stats.present }}</div>
            <div class="stat-label">正常出勤</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card late">
          <div class="stat-content">
            <div class="stat-value">{{ stats.late }}</div>
            <div class="stat-label">迟到</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card absent">
          <div class="stat-content">
            <div class="stat-value">{{ stats.absent }}</div>
            <div class="stat-label">旷课</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card leave">
          <div class="stat-content">
            <div class="stat-value">{{ stats.leave }}</div>
            <div class="stat-label">请假</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索栏 -->
    <el-card class="search-card" shadow="never">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="学号">
          <el-input
            v-model="searchForm.student_no"
            placeholder="请输入学号"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="学生姓名">
          <el-input
            v-model="searchForm.student_name"
            placeholder="请输入学生姓名"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="课程名称">
          <el-input
            v-model="searchForm.course_name"
            placeholder="请输入课程名称"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="考勤状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable>
            <el-option label="正常" value="present" />
            <el-option label="迟到" value="late" />
            <el-option label="旷课" value="absent" />
            <el-option label="请假" value="leave" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="handleDateChange"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格 -->
    <el-card class="table-card" shadow="never">
      <el-table
        :data="tableData"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="student_no" label="学号" width="120" />
        <el-table-column prop="student_name" label="学生姓名" width="100" />
        <el-table-column prop="class_name" label="班级" width="120" />
        <el-table-column prop="course_name" label="课程名称" min-width="150" />
        <el-table-column prop="date" label="考勤日期" width="120" />
        <el-table-column prop="status" label="考勤状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" effect="dark">
              {{ row.status_text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
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
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 录入/编辑考勤弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑考勤' : '录入考勤'"
      width="500px"
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="学生" prop="student_id">
          <el-select
            v-model="form.student_id"
            filterable
            remote
            reserve-keyword
            placeholder="请输入学号或姓名搜索"
            :remote-method="searchStudents"
            :loading="studentLoading"
            :disabled="isEdit"
          >
            <el-option
              v-for="item in studentOptions"
              :key="item.id"
              :label="`${item.student_no} - ${item.name}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="课程" prop="course_id">
          <el-select
            v-model="form.course_id"
            placeholder="请选择课程"
            :disabled="isEdit"
          >
            <el-option
              v-for="item in courseOptions"
              :key="item.id"
              :label="`${item.course_code} - ${item.course_name}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="考勤日期" prop="date">
          <el-date-picker
            v-model="form.date"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :disabled="isEdit"
          />
        </el-form-item>
        <el-form-item label="考勤状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio-button value="present">
              <el-tag type="success" effect="dark" size="small">正常</el-tag>
            </el-radio-button>
            <el-radio-button value="late">
              <el-tag type="warning" effect="dark" size="small">迟到</el-tag>
            </el-radio-button>
            <el-radio-button value="absent">
              <el-tag type="danger" effect="dark" size="small">旷课</el-tag>
            </el-radio-button>
            <el-radio-button value="leave">
              <el-tag type="info" effect="dark" size="small">请假</el-tag>
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input
            v-model="form.remark"
            type="textarea"
            :rows="3"
            placeholder="请输入备注信息（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <ImportAttendancesDialog
      v-model="showImportDialog"
      @success="handleImportSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Search, Refresh, Upload } from '@element-plus/icons-vue'
import ImportAttendancesDialog from '@/components/ImportAttendancesDialog.vue'
import {
  getAttendanceList,
  createAttendance,
  updateAttendance,
  deleteAttendance,
  getAttendanceStats,
  getAttendanceCourses
} from '@/api/attendances'
import { getStudentList } from '@/api/student'

// 状态类型映射
const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    present: 'success',
    late: 'warning',
    absent: 'danger',
    leave: 'info'
  }
  return map[status] || ''
}

// 搜索表单
const searchForm = reactive({
  student_no: '',
  student_name: '',
  course_name: '',
  status: '',
  start_date: '',
  end_date: ''
})

// 日期范围
const dateRange = ref<string[]>([])

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 统计数据
const stats = reactive({
  total: 0,
  present: 0,
  late: 0,
  absent: 0,
  leave: 0,
  attendance_rate: 0
})

// 表格数据
const tableData = ref<any[]>([])
const loading = ref(false)

// 导入对话框
const showImportDialog = ref(false)

// 弹窗相关
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const submitLoading = ref(false)

// 表单数据
const form = reactive({
  student_id: null as number | null,
  course_id: null as number | null,
  date: '',
  status: 'present',
  remark: ''
})

// 表单验证规则
const rules: FormRules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  course_id: [{ required: true, message: '请选择课程', trigger: 'change' }],
  date: [{ required: true, message: '请选择考勤日期', trigger: 'change' }],
  status: [{ required: true, message: '请选择考勤状态', trigger: 'change' }]
}

// 下拉选项
const studentOptions = ref<any[]>([])
const studentLoading = ref(false)
const courseOptions = ref<any[]>([])

// 加载统计数据
const loadStats = async () => {
  try {
    const res = await getAttendanceStats()
    Object.assign(stats, res)
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const res = await getAttendanceList({
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm
    })
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载课程选项
const loadCourses = async () => {
  try {
    const res = await getAttendanceCourses()
    courseOptions.value = res.items || []
  } catch (error) {
    console.error('加载课程失败:', error)
  }
}

// 搜索学生（支持学号或姓名）
const searchStudents = async (query: string) => {
  if (!query) {
    studentOptions.value = []
    return
  }
  studentLoading.value = true
  try {
    // 如果输入的是数字开头，按学号搜索；否则按姓名搜索
    const isStudentNo = /^\d/.test(query)
    const res = await getStudentList({
      page: 1,
      page_size: 20,
      ...(isStudentNo ? { student_no: query } : { name: query })
    })
    studentOptions.value = res.items || []
  } catch (error) {
    console.error('搜索学生失败:', error)
  } finally {
    studentLoading.value = false
  }
}

// 日期范围变化
const handleDateChange = (val: string[] | null) => {
  if (val && val.length === 2) {
    searchForm.start_date = val[0]
    searchForm.end_date = val[1]
  } else {
    searchForm.start_date = ''
    searchForm.end_date = ''
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadData()
}

// 重置
const handleReset = () => {
  Object.assign(searchForm, {
    student_no: '',
    student_name: '',
    course_name: '',
    status: '',
    start_date: '',
    end_date: ''
  })
  dateRange.value = []
  handleSearch()
}

// 分页
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  loadData()
}

const handlePageChange = (page: number) => {
  pagination.page = page
  loadData()
}

// 打开弹窗
const openDialog = (row?: any) => {
  isEdit.value = !!row
  editId.value = row?.id || null

  if (row) {
    // 编辑模式
    form.student_id = row.student_id
    form.course_id = row.course_id
    form.date = row.date
    form.status = row.status
    form.remark = row.remark || ''

    // 加载当前学生到选项中
    studentOptions.value = [{
      id: row.student_id,
      student_no: row.student_no,
      name: row.student_name
    }]
  } else {
    // 新增模式
    resetForm()
    // 默认今天日期
    form.date = new Date().toISOString().split('T')[0]
  }

  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(form, {
    student_id: null,
    course_id: null,
    date: '',
    status: 'present',
    remark: ''
  })
  studentOptions.value = []
  formRef.value?.resetFields()
}

// 提交表单
const handleSubmit = async () => {
  const valid = await formRef.value?.validate()
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value && editId.value) {
      await updateAttendance(editId.value, {
        status: form.status,
        remark: form.remark
      })
      ElMessage.success('考勤记录更新成功')
    } else {
      await createAttendance(form)
      ElMessage.success('考勤记录创建成功')
    }
    dialogVisible.value = false
    loadData()
    loadStats() // 刷新统计
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

// 删除
const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${row.student_name} 在 ${row.date} 的考勤记录吗？`,
      '提示',
      { type: 'warning' }
    )
    await deleteAttendance(row.id)
    ElMessage.success('删除成功')
    loadData()
    loadStats() // 刷新统计
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 导入成功后刷新
const handleImportSuccess = () => {
  loadData()
  loadStats()
}

onMounted(() => {
  loadData()
  loadStats()
  loadCourses()
})
</script>

<style scoped lang="scss">
.attendance-management {
  padding: 20px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }

    .header-actions {
      display: flex;
      gap: 10px;
    }
  }

  .stat-row {
    margin-bottom: 20px;

    .stat-card {
      :deep(.el-card__body) {
        padding: 20px;
      }

      .stat-content {
        text-align: center;

        .stat-value {
          font-size: 32px;
          font-weight: 600;
          line-height: 1.2;
        }

        .stat-label {
          font-size: 14px;
          color: var(--el-text-color-secondary);
          margin-top: 8px;
        }
      }

      &.present {
        .stat-value { color: var(--el-color-success); }
      }

      &.late {
        .stat-value { color: var(--el-color-warning); }
      }

      &.absent {
        .stat-value { color: var(--el-color-danger); }
      }

      &.leave {
        .stat-value { color: var(--el-color-info); }
      }
    }
  }

  .search-card {
    margin-bottom: 20px;

    .search-form {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
  }

  .table-card {
    .pagination-wrapper {
      display: flex;
      justify-content: flex-end;
      margin-top: 20px;
    }
  }
}
</style>
