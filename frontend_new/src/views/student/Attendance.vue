<template>
  <div class="student-attendance">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>我的考勤</h2>
      <p class="subtitle">查看各课程的考勤记录和出勤统计</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card normal">
          <div class="stat-icon"><el-icon><CircleCheck /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.normal || 0 }}</div>
            <div class="stat-label">正常出勤</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card late">
          <div class="stat-icon"><el-icon><Clock /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.late || 0 }}</div>
            <div class="stat-label">迟到</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card absent">
          <div class="stat-icon"><el-icon><CircleClose /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.absent || 0 }}</div>
            <div class="stat-label">缺勤</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card leave">
          <div class="stat-icon"><el-icon><Document /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.leave || 0 }}</div>
            <div class="stat-label">请假</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 出勤率进度条 -->
    <el-card shadow="hover" class="rate-card">
      <div class="rate-header">
        <span>总体出勤率</span>
        <span class="rate-value" :class="getRateClass(attendanceRate)">{{ attendanceRate }}%</span>
      </div>
      <el-progress
        :percentage="attendanceRate"
        :color="getRateColor(attendanceRate)"
        :stroke-width="20"
      />
    </el-card>

    <!-- 筛选工具栏 -->
    <el-card shadow="hover" class="filter-card">
      <div class="filters">
        <el-select v-model="filters.course" placeholder="选择课程" clearable style="width: 200px">
          <el-option v-for="c in courses" :key="c" :label="c" :value="c" />
        </el-select>
        <el-select v-model="filters.status" placeholder="考勤状态" clearable style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="正常" value="normal" />
          <el-option label="迟到" value="late" />
          <el-option label="缺勤" value="absent" />
          <el-option label="请假" value="leave" />
        </el-select>
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
      </div>
    </el-card>

    <!-- 考勤记录表格 -->
    <el-card shadow="hover" class="table-card">
      <el-table :data="records" style="width: 100%" v-loading="loading">
        <el-table-column prop="course_name" label="课程名称" min-width="150" />
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="week" label="周次" width="80" align="center" />
        <el-table-column prop="time" label="节次" width="80" align="center" />
        <el-table-column prop="status" label="考勤状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.remark || '-' }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadRecords"
          @current-change="loadRecords"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { CircleCheck, Clock, CircleClose, Document } from '@element-plus/icons-vue'
import { getStudentAttendance } from '@/api/student'

interface AttendanceRecord {
  id: number
  course_name: string
  date: string
  week: number
  time: string
  status: string
  remark?: string
}

interface Stats {
  normal: number
  late: number
  absent: number
  leave: number
}

const loading = ref(false)
const records = ref<AttendanceRecord[]>([])
const courses = ref<string[]>([])
const stats = ref<Stats>({
  normal: 0,
  late: 0,
  absent: 0,
  leave: 0
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const filters = reactive({
  course: '',
  status: '',
  dateRange: null as [Date, Date] | null
})

// 计算出勤率
const attendanceRate = computed(() => {
  const total = stats.value.normal + stats.value.late + stats.value.absent + stats.value.leave
  if (total === 0) return 100
  return Math.round(((stats.value.normal + stats.value.late) / total) * 100)
})

// 获取出勤率颜色
const getRateColor = (rate: number) => {
  if (rate >= 90) return '#67c23a'
  if (rate >= 70) return '#e6a23c'
  return '#f56c6c'
}

// 获取出勤率样式类
const getRateClass = (rate: number) => {
  if (rate >= 90) return 'rate-good'
  if (rate >= 70) return 'rate-warning'
  return 'rate-danger'
}

// 获取状态名称
const getStatusName = (status: string) => {
  const map: Record<string, string> = {
    normal: '正常',
    late: '迟到',
    absent: '缺勤',
    leave: '请假'
  }
  return map[status] || status
}

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const map: Record<string, string> = {
    normal: 'success',
    late: 'warning',
    absent: 'danger',
    leave: 'info'
  }
  return map[status] || ''
}

// 加载考勤记录
const loadRecords = async () => {
  loading.value = true
  try {
    const res = await getStudentAttendance({
      page: pagination.page,
      page_size: pagination.pageSize,
      course: filters.course || undefined,
      status: filters.status || undefined,
      start_date: filters.dateRange?.[0]?.toISOString(),
      end_date: filters.dateRange?.[1]?.toISOString()
    })
    records.value = res.items || []
    pagination.total = res.total || 0

    // 提取课程列表
    const courseSet = new Set<string>()
    res.items?.forEach((r: AttendanceRecord) => {
      if (r.course_name) courseSet.add(r.course_name)
    })
    courses.value = Array.from(courseSet)

    // 如果返回了统计信息
    if (res.stats) {
      stats.value = res.stats
    }
  } catch (error) {
    console.error('加载考勤记录失败:', error)
  } finally {
    loading.value = false
  }
}

watch(filters, () => {
  pagination.page = 1
  loadRecords()
}, { deep: true })

onMounted(() => {
  loadRecords()
})
</script>

<style scoped lang="scss">
.student-attendance {
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
      display: flex;
      align-items: center;
      padding: 16px;

      .stat-icon {
        width: 50px;
        height: 50px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        color: #fff;
        margin-right: 12px;
      }

      .stat-content {
        .stat-value {
          font-size: 28px;
          font-weight: 600;
        }

        .stat-label {
          font-size: 14px;
          color: var(--el-text-color-secondary);
        }
      }

      &.normal .stat-icon { background: linear-gradient(135deg, #67c23a, #85ce61); }
      &.late .stat-icon { background: linear-gradient(135deg, #e6a23c, #f5d442); }
      &.absent .stat-icon { background: linear-gradient(135deg, #f56c6c, #fab6b6); }
      &.leave .stat-icon { background: linear-gradient(135deg, #909399, #c0c4cc); }
    }
  }

  .rate-card {
    margin-bottom: 20px;

    .rate-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;

      .rate-value {
        font-size: 24px;
        font-weight: 600;

        &.rate-good { color: #67c23a; }
        &.rate-warning { color: #e6a23c; }
        &.rate-danger { color: #f56c6c; }
      }
    }
  }

  .filter-card {
    margin-bottom: 16px;

    .filters {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    padding: 16px 0 0;
  }
}
</style>
