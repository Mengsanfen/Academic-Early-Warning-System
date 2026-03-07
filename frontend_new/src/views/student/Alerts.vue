<template>
  <div class="student-alerts">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>我的预警</h2>
      <p class="subtitle">查看您的学业预警记录和处理进度</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card total">
          <div class="stat-value">{{ stats.total || 0 }}</div>
          <div class="stat-label">预警总数</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card high">
          <div class="stat-value">{{ stats.high || 0 }}</div>
          <div class="stat-label">高风险</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card medium">
          <div class="stat-value">{{ stats.medium || 0 }}</div>
          <div class="stat-label">中风险</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card low">
          <div class="stat-value">{{ stats.low || 0 }}</div>
          <div class="stat-label">低风险</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选工具栏 -->
    <el-card shadow="hover" class="filter-card">
      <div class="filters">
        <el-select v-model="filters.type" placeholder="预警类型" clearable style="width: 140px">
          <el-option label="全部类型" value="" />
          <el-option label="成绩预警" value="grade" />
          <el-option label="考勤预警" value="attendance" />
          <el-option label="学分预警" value="credit" />
          <el-option label="综合预警" value="comprehensive" />
        </el-select>
        <el-select v-model="filters.level" placeholder="风险等级" clearable style="width: 120px">
          <el-option label="全部等级" value="" />
          <el-option label="高风险" value="high" />
          <el-option label="中风险" value="medium" />
          <el-option label="低风险" value="low" />
        </el-select>
        <el-select v-model="filters.status" placeholder="处理状态" clearable style="width: 120px">
          <el-option label="全部状态" value="" />
          <el-option label="待处理" value="pending" />
          <el-option label="处理中" value="processing" />
          <el-option label="已解决" value="resolved" />
        </el-select>
      </div>
    </el-card>

    <!-- 预警列表 -->
    <el-card shadow="hover" class="table-card">
      <el-table :data="alerts" style="width: 100%" v-loading="loading">
        <el-table-column prop="alert_type" label="预警类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.alert_type)">
              {{ getTypeName(row.alert_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alert_level" label="风险等级" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getLevelTagType(row.alert_level)" effect="dark">
              {{ getLevelName(row.alert_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="预警描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="suggestion" label="建议措施" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.suggestion || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link @click="showDetail(row)">
              详情
            </el-button>
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
          @size-change="loadAlerts"
          @current-change="loadAlerts"
        />
      </div>
    </el-card>

    <!-- 预警详情对话框 -->
    <el-dialog v-model="detailVisible" title="预警详情" width="500px">
      <el-descriptions :column="1" border v-if="currentAlert">
        <el-descriptions-item label="预警类型">
          <el-tag :type="getTypeTagType(currentAlert.alert_type)">
            {{ getTypeName(currentAlert.alert_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="风险等级">
          <el-tag :type="getLevelTagType(currentAlert.alert_level)" effect="dark">
            {{ getLevelName(currentAlert.alert_level) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="预警描述">{{ currentAlert.description }}</el-descriptions-item>
        <el-descriptions-item label="建议措施">{{ currentAlert.suggestion || '暂无' }}</el-descriptions-item>
        <el-descriptions-item label="处理状态">
          <el-tag :type="getStatusTagType(currentAlert.status)">
            {{ getStatusName(currentAlert.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="生成时间">{{ formatDate(currentAlert.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDate(currentAlert.updated_at) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { getStudentAlerts } from '@/api/student'

interface Alert {
  id: number
  alert_type: string
  alert_level: string
  description: string
  suggestion?: string
  status: string
  created_at: string
  updated_at?: string
}

interface Stats {
  total: number
  high: number
  medium: number
  low: number
}

const loading = ref(false)
const alerts = ref<Alert[]>([])
const stats = ref<Stats>({
  total: 0,
  high: 0,
  medium: 0,
  low: 0
})
const detailVisible = ref(false)
const currentAlert = ref<Alert | null>(null)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const filters = reactive({
  type: '',
  level: '',
  status: ''
})

// 获取类型名称
const getTypeName = (type: string) => {
  const map: Record<string, string> = {
    grade: '成绩预警',
    attendance: '考勤预警',
    credit: '学分预警',
    comprehensive: '综合预警'
  }
  return map[type] || type
}

// 获取类型标签颜色
const getTypeTagType = (type: string) => {
  const map: Record<string, string> = {
    grade: 'danger',
    attendance: 'warning',
    credit: 'info',
    comprehensive: ''
  }
  return map[type] || ''
}

// 获取等级名称
const getLevelName = (level: string) => {
  const map: Record<string, string> = {
    high: '高',
    medium: '中',
    low: '低'
  }
  return map[level] || level
}

// 获取等级标签颜色
const getLevelTagType = (level: string) => {
  const map: Record<string, string> = {
    high: 'danger',
    medium: 'warning',
    low: 'info'
  }
  return map[level] || 'info'
}

// 获取状态名称
const getStatusName = (status: string) => {
  const map: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    resolved: '已解决'
  }
  return map[status] || status
}

// 获取状态标签颜色
const getStatusTagType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'danger',
    processing: 'warning',
    resolved: 'success'
  }
  return map[status] || ''
}

// 格式化日期
const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 显示详情
const showDetail = (alert: Alert) => {
  currentAlert.value = alert
  detailVisible.value = true
}

// 加载预警数据
const loadAlerts = async () => {
  loading.value = true
  try {
    const res = await getStudentAlerts({
      page: pagination.page,
      page_size: pagination.pageSize,
      type: filters.type || undefined,
      level: filters.level || undefined,
      status: filters.status || undefined
    })
    alerts.value = res.items || []
    pagination.total = res.total || 0

    // 如果返回了统计信息
    if (res.stats) {
      stats.value = res.stats
    } else {
      // 从列表计算统计
      stats.value = {
        total: pagination.total,
        high: alerts.value.filter(a => a.alert_level === 'high').length,
        medium: alerts.value.filter(a => a.alert_level === 'medium').length,
        low: alerts.value.filter(a => a.alert_level === 'low').length
      }
    }
  } catch (error) {
    console.error('加载预警数据失败:', error)
  } finally {
    loading.value = false
  }
}

watch(filters, () => {
  pagination.page = 1
  loadAlerts()
}, { deep: true })

onMounted(() => {
  loadAlerts()
})
</script>

<style scoped lang="scss">
.student-alerts {
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
      border-radius: 8px;

      .stat-value {
        font-size: 32px;
        font-weight: 600;
      }

      .stat-label {
        font-size: 14px;
        color: var(--el-text-color-secondary);
        margin-top: 4px;
      }

      &.total {
        background: linear-gradient(135deg, #f5f7fa, #e4e7ed);
        .stat-value { color: #606266; }
      }

      &.high {
        background: linear-gradient(135deg, #fef0f0, #fde2e2);
        .stat-value { color: #f56c6c; }
      }

      &.medium {
        background: linear-gradient(135deg, #fdf6ec, #faecd8);
        .stat-value { color: #e6a23c; }
      }

      &.low {
        background: linear-gradient(135deg, #f4f4f5, #e9e9eb);
        .stat-value { color: #909399; }
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
