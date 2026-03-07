<template>
  <div class="score-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>成绩管理</h2>
      <div class="header-actions">
        <el-button @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>
          批量导入
        </el-button>
        <el-button type="primary" @click="openDialog()">
          <el-icon><Plus /></el-icon>
          录入成绩
        </el-button>
      </div>
    </div>

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
        <el-form-item label="学期">
          <el-select v-model="searchForm.semester" placeholder="全部学期" clearable>
            <el-option
              v-for="item in semesters"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="及格状态">
          <el-select v-model="searchForm.is_passed" placeholder="全部" clearable>
            <el-option label="及格" :value="true" />
            <el-option label="不及格" :value="false" />
          </el-select>
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
        <el-table-column prop="course_code" label="课程代码" width="100" />
        <el-table-column prop="course_name" label="课程名称" min-width="150" />
        <el-table-column prop="credit" label="学分" width="80" align="center" />
        <el-table-column prop="score" label="成绩" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_passed ? 'success' : 'danger'" effect="plain">
              {{ row.score }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="semester" label="学期" width="120" />
        <el-table-column prop="exam_type" label="考试类型" width="100" />
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

    <!-- 录入/编辑成绩弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑成绩' : '录入成绩'"
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
        <el-form-item label="成绩" prop="score">
          <el-input-number
            v-model="form.score"
            :min="0"
            :max="100"
            :precision="1"
            placeholder="请输入成绩"
          />
        </el-form-item>
        <el-form-item label="学期" prop="semester">
          <el-input v-model="form.semester" placeholder="如：2024-2025-1" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="考试类型" prop="exam_type">
          <el-select v-model="form.exam_type" placeholder="请选择考试类型">
            <el-option label="期末" value="期末" />
            <el-option label="补考" value="补考" />
            <el-option label="重修" value="重修" />
          </el-select>
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
    <ImportScoresDialog
      v-model="showImportDialog"
      @success="handleImportSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Search, Refresh, Upload } from '@element-plus/icons-vue'
import ImportScoresDialog from '@/components/ImportScoresDialog.vue'
import {
  getScoreList,
  createScore,
  updateScore,
  deleteScore,
  getScoreCourses,
  getScoreSemesters
} from '@/api/scores'
import { getStudentList } from '@/api/student'

// 搜索表单
const searchForm = reactive({
  student_no: '',
  student_name: '',
  course_name: '',
  semester: '',
  is_passed: null as boolean | null
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
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
  score: 60,
  semester: '',
  exam_type: '期末'
})

// 表单验证规则
const rules: FormRules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  course_id: [{ required: true, message: '请选择课程', trigger: 'change' }],
  score: [{ required: true, message: '请输入成绩', trigger: 'blur' }],
  semester: [{ required: true, message: '请输入学期', trigger: 'blur' }]
}

// 下拉选项
const studentOptions = ref<any[]>([])
const studentLoading = ref(false)
const courseOptions = ref<any[]>([])
const semesters = ref<string[]>([])

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const res = await getScoreList({
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
    const res = await getScoreCourses()
    courseOptions.value = res.items || []
  } catch (error) {
    console.error('加载课程失败:', error)
  }
}

// 加载学期选项
const loadSemesters = async () => {
  try {
    const res = await getScoreSemesters()
    semesters.value = res.items || []
  } catch (error) {
    console.error('加载学期失败:', error)
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
    semester: '',
    is_passed: null
  })
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
    form.score = row.score
    form.semester = row.semester
    form.exam_type = row.exam_type || '期末'

    // 加载当前学生到选项中
    studentOptions.value = [{
      id: row.student_id,
      student_no: row.student_no,
      name: row.student_name
    }]
  } else {
    // 新增模式
    resetForm()
  }

  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(form, {
    student_id: null,
    course_id: null,
    score: 60,
    semester: '',
    exam_type: '期末'
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
      await updateScore(editId.value, {
        score: form.score,
        exam_type: form.exam_type
      })
      ElMessage.success('成绩更新成功')
    } else {
      await createScore(form)
      ElMessage.success('成绩录入成功')
    }
    dialogVisible.value = false
    loadData()
    loadSemesters() // 刷新学期列表
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
      `确定要删除 ${row.student_name} 的 ${row.course_name} 成绩记录吗？`,
      '提示',
      { type: 'warning' }
    )
    await deleteScore(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 导入成功后刷新
const handleImportSuccess = () => {
  loadData()
  loadSemesters()
}

onMounted(() => {
  loadData()
  loadCourses()
  loadSemesters()
})
</script>

<style scoped lang="scss">
.score-management {
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
