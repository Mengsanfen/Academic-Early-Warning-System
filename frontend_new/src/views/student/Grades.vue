<template>
  <div class="student-grades">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>我的成绩</h2>
      <p class="subtitle">查看各学期课程成绩和学分情况</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.totalCourses || 0 }}</div>
          <div class="stat-label">课程总数</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.avgScore || '--' }}</div>
          <div class="stat-label">平均成绩</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.passedCourses || 0 }}</div>
          <div class="stat-label">通过课程</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card highlight">
          <div class="stat-value">{{ stats.failedCourses || 0 }}</div>
          <div class="stat-label">不及格课程</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选工具栏 -->
    <el-card shadow="hover" class="filter-card">
      <div class="filters">
        <el-select v-model="filters.semester" placeholder="选择学期" clearable style="width: 160px">
          <el-option v-for="sem in semesters" :key="sem" :label="sem" :value="sem" />
        </el-select>
        <el-select v-model="filters.status" placeholder="成绩状态" clearable style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="及格" value="pass" />
          <el-option label="不及格" value="fail" />
        </el-select>
      </div>
    </el-card>

    <!-- 成绩表格 -->
    <el-card shadow="hover" class="table-card">
      <el-table :data="grades" style="width: 100%" v-loading="loading">
        <el-table-column prop="course_name" label="课程名称" min-width="180" />
        <el-table-column prop="course_code" label="课程代码" width="120" />
        <el-table-column prop="credit" label="学分" width="80" align="center" />
        <el-table-column prop="semester" label="学期" width="120" />
        <el-table-column prop="score" label="成绩" width="100" align="center">
          <template #default="{ row }">
            <span :class="getScoreClass(row.score)">{{ row.score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="grade_point" label="绩点" width="80" align="center">
          <template #default="{ row }">
            <span>{{ row.grade_point?.toFixed(1) || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.score >= 60 ? 'success' : 'danger'">
              {{ row.score >= 60 ? '及格' : '不及格' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { getStudentGrades } from '@/api/student'

interface Grade {
  id: number
  course_name: string
  course_code: string
  credit: number
  semester: string
  score: number
  grade_point: number
}

interface Stats {
  totalCourses: number
  avgScore: number
  passedCourses: number
  failedCourses: number
}

const loading = ref(false)
const grades = ref<Grade[]>([])
const semesters = ref<string[]>([])
const stats = ref<Stats>({
  totalCourses: 0,
  avgScore: 0,
  passedCourses: 0,
  failedCourses: 0
})

const filters = reactive({
  semester: '',
  status: ''
})

// 获取成绩样式
const getScoreClass = (score: number) => {
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-pass'
  return 'score-fail'
}

// 加载成绩数据
const loadGrades = async () => {
  loading.value = true
  try {
    const res = await getStudentGrades({
      semester: filters.semester || undefined,
      status: filters.status || undefined
    })
    grades.value = res.items || []

    // 提取学期列表
    const semSet = new Set<string>()
    res.items?.forEach((g: Grade) => {
      if (g.semester) semSet.add(g.semester)
    })
    semesters.value = Array.from(semSet)

    // 计算统计数据
    const items = res.items || []
    stats.value = {
      totalCourses: items.length,
      avgScore: items.length ? Math.round(items.reduce((sum: number, g: Grade) => sum + g.score, 0) / items.length) : 0,
      passedCourses: items.filter((g: Grade) => g.score >= 60).length,
      failedCourses: items.filter((g: Grade) => g.score < 60).length
    }
  } catch (error) {
    console.error('加载成绩失败:', error)
  } finally {
    loading.value = false
  }
}

watch(filters, () => {
  loadGrades()
}, { deep: true })

onMounted(() => {
  loadGrades()
})
</script>

<style scoped lang="scss">
.student-grades {
  padding: 20px;

  .page-header {
    margin-bottom: 20px;

    h2 {
      margin: 0 0 8px 0;
      font-size: 24px;
      font-weight: 600;
    }

    .subtitle {
      margin: 0;
      color: var(--el-text-color-secondary);
      font-size: 14px;
    }
  }

  .stat-cards {
    margin-bottom: 20px;

    .stat-card {
      text-align: center;
      padding: 16px;

      .stat-value {
        font-size: 32px;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }

      .stat-label {
        font-size: 14px;
        color: var(--el-text-color-secondary);
        margin-top: 4px;
      }

      &.highlight .stat-value {
        color: var(--el-color-danger);
      }
    }
  }

  .filter-card {
    margin-bottom: 16px;

    .filters {
      display: flex;
      gap: 12px;
    }
  }

  .table-card {
    .score-excellent {
      color: #67c23a;
      font-weight: 600;
    }

    .score-good {
      color: #409eff;
      font-weight: 600;
    }

    .score-pass {
      color: #e6a23c;
    }

    .score-fail {
      color: #f56c6c;
      font-weight: 600;
    }
  }
}
</style>
