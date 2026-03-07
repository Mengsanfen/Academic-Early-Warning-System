<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">学生管理</h1>
      <div class="page-actions">
        <el-button type="primary" @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>
          批量导入
        </el-button>
      </div>
    </div>

    <!-- 搜索表单 -->
    <div class="search-form card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="学号">
          <el-input v-model="searchForm.student_no" placeholder="请输入学号" clearable />
        </el-form-item>
        <el-form-item label="学生姓名">
          <el-input v-model="searchForm.name" placeholder="请输入学生姓名" clearable />
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="selectedClassId" placeholder="请选择班级" clearable style="width: 200px">
            <el-option
              v-for="cls in classes"
              :key="cls.id"
              :label="cls.name"
              :value="cls.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 表格 -->
    <div class="page-content">
      <el-table :data="students" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="student_no" label="学号" width="140" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="gender" label="性别" width="80">
          <template #default="{ row }">
            {{ formatGender(row.gender) }}
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" width="150" />
        <el-table-column prop="phone" label="联系电话" width="140" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '在读' : row.status === 'suspended' ? '休学' : '毕业' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchStudents"
          @current-change="fetchStudents"
        />
      </div>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="学生详情" size="600px">
      <div v-if="currentStudent" class="student-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="学号">{{ currentStudent.student_no }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ currentStudent.name }}</el-descriptions-item>
          <el-descriptions-item label="性别">
            {{ formatGender(currentStudent.gender) }}
          </el-descriptions-item>
          <el-descriptions-item label="班级">{{ currentStudent.class_name }}</el-descriptions-item>
          <el-descriptions-item label="入学年份">{{ currentStudent.enroll_year }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentStudent.status === 'active' ? 'success' : 'info'" size="small">
              {{ currentStudent.status === 'active' ? '在读' : currentStudent.status === 'suspended' ? '休学' : '毕业' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ currentStudent.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ currentStudent.email || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">成绩信息</el-divider>
        <el-table :data="scores" size="small" max-height="200">
          <el-table-column prop="course_name" label="课程" />
          <el-table-column prop="score" label="成绩" width="80" />
          <el-table-column label="是否通过" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_passed ? 'success' : 'danger'" size="small">
                {{ row.is_passed ? '通过' : '未通过' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>

    <!-- 导入对话框 -->
    <ImportStudentsDialog
      v-model="showImportDialog"
      @success="handleImportSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Upload } from '@element-plus/icons-vue'
import { getStudents, getStudentScores, getClasses } from '@/api/student'
import type { ClassInfo } from '@/api/student'
import ImportStudentsDialog from '@/components/ImportStudentsDialog.vue'
import type { Student, Score } from '@/types'

const loading = ref(false)
const detailVisible = ref(false)
const showImportDialog = ref(false)
const students = ref<Student[]>([])
const currentStudent = ref<Student | null>(null)
const scores = ref<Score[]>([])
const classes = ref<ClassInfo[]>([])
const selectedClassId = ref<number | undefined>(undefined)

const searchForm = reactive({
  name: '',
  student_no: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 格式化性别显示（兼容中文和英文两种格式）
function formatGender(gender: string | null | undefined): string {
  if (!gender) return '-'
  const genderMap: Record<string, string> = {
    'male': '男',
    'female': '女',
    '男': '男',
    '女': '女',
    'M': '男',
    'F': '女',
    '1': '男',
    '0': '女'
  }
  return genderMap[gender] || gender
}

async function fetchStudents() {
  loading.value = true
  try {
    const res = await getStudents({
      page: pagination.page,
      page_size: pagination.page_size,
      name: searchForm.name || undefined,
      student_no: searchForm.student_no || undefined,
      class_id: selectedClassId.value
    })
    students.value = res.items
    pagination.total = res.total
  } catch (error) {
    console.error('获取学生列表失败', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchStudents()
}

function handleReset() {
  searchForm.name = ''
  searchForm.student_no = ''
  selectedClassId.value = undefined
  handleSearch()
}

async function viewDetail(student: Student) {
  currentStudent.value = student
  detailVisible.value = true

  try {
    const res = await getStudentScores(student.id)
    scores.value = res.items
  } catch (error) {
    console.error('获取成绩失败', error)
  }
}

// 导入成功后刷新列表
function handleImportSuccess() {
  fetchStudents()
  fetchClassList()  // 同时刷新班级列表
}

// 获取班级列表
async function fetchClassList() {
  try {
    const res = await getClasses()
    classes.value = res.items
  } catch (error) {
    console.error('获取班级列表失败', error)
  }
}

onMounted(() => {
  fetchClassList()
  fetchStudents()
})
</script>

<style lang="scss" scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  .page-title {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
  }
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.student-detail {
  padding: 0 20px;
}
</style>
