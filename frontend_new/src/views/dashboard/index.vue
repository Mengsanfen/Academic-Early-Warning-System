<template>
  <div class="dashboard-container">
    <!-- 统计卡片 -->
    <div class="stat-cards">
      <div class="stat-card">
        <div class="stat-icon blue">
          <el-icon :size="28"><User /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ overview.student_count }}</div>
          <div class="stat-label">学生总数</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon orange">
          <el-icon :size="28"><Bell /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ overview.alert_count?.pending || 0 }}</div>
          <div class="stat-label">待处理预警</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon red">
          <el-icon :size="28"><Warning /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ overview.alert_count?.processing || 0 }}</div>
          <div class="stat-label">处理中预警</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon green">
          <el-icon :size="28"><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ overview.alert_count?.resolved || 0 }}</div>
          <div class="stat-label">已解决预警</div>
        </div>
      </div>
    </div>
    
    <!-- 图表区域 -->
    <div class="chart-row">
      <div class="chart-card">
        <div class="chart-header">
          <h3>预警级别分布</h3>
        </div>
        <div class="chart-content">
          <PieChart :data="levelData" />
        </div>
      </div>
      
      <div class="chart-card">
        <div class="chart-header">
          <h3>近7日预警趋势</h3>
        </div>
        <div class="chart-content">
          <LineChart :data="trendData" />
        </div>
      </div>
    </div>
    
    <!-- 最新预警列表 -->
    <div class="alert-list-card">
      <div class="card-header">
        <h3>最新预警</h3>
        <el-button text type="primary" @click="$router.push('/alerts')">
          查看全部
        </el-button>
      </div>
      
      <el-table :data="overview.recent_alerts" stripe style="width: 100%">
        <el-table-column prop="student_name" label="学生姓名" width="120" />
        <el-table-column prop="student_no" label="学号" width="140" />
        <el-table-column prop="rule_name" label="预警规则" />
        <el-table-column label="预警级别" width="100">
          <template #default="{ row }">
            <span :class="['alert-level-tag', row.level]">
              {{ levelText[row.level] }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType[row.status]" size="small">
              {{ statusText[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="viewAlert(row.id)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { User, Bell, Warning, CircleCheck } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { getOverview, getTrend } from '@/api/dashboard'
import type { DashboardOverview, TrendData } from '@/types'
import PieChart from '@/components/Charts/PieChart.vue'
import LineChart from '@/components/Charts/LineChart.vue'

const router = useRouter()

const overview = ref<DashboardOverview>({
  student_count: 0,
  alert_count: { total: 0, pending: 0, processing: 0, resolved: 0 },
  alert_by_level: {},
  alert_by_type: {},
  recent_alerts: []
})

const trendData = ref<TrendData>({ days: 7, data: [] })

const levelText: Record<string, string> = {
  warning: '警告',
  serious: '严重',
  urgent: '紧急'
}

const statusText: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  ignored: '已忽略'
}

const statusType: Record<string, string> = {
  pending: 'warning',
  processing: 'danger',
  resolved: 'success',
  ignored: 'info'
}

const levelData = computed(() => {
  return [
    { name: '警告', value: overview.value.alert_by_level?.warning || 0 },
    { name: '严重', value: overview.value.alert_by_level?.serious || 0 },
    { name: '紧急', value: overview.value.alert_by_level?.urgent || 0 }
  ]
})

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

function viewAlert(id: number) {
  router.push(`/alerts?id=${id}`)
}

async function fetchData() {
  try {
    const [overviewRes, trendRes] = await Promise.all([
      getOverview(),
      getTrend(7)
    ])
    overview.value = overviewRes
    trendData.value = trendRes
  } catch (error) {
    console.error('获取数据失败', error)
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style lang="scss" scoped>
.dashboard-container {
  padding: 20px;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
  
  .chart-header {
    margin-bottom: 16px;
    
    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }
  
  .chart-content {
    height: 300px;
  }
}

.alert-list-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }
}

.alert-level-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  
  &.warning {
    background-color: rgba(230, 162, 60, 0.1);
    color: #E6A23C;
  }
  
  &.serious {
    background-color: rgba(245, 108, 108, 0.1);
    color: #F56C6C;
  }
  
  &.urgent {
    background-color: rgba(245, 108, 108, 0.15);
    color: #F56C6C;
    font-weight: 600;
  }
}

@media (max-width: 1200px) {
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stat-cards {
    grid-template-columns: 1fr;
  }
  
  .chart-row {
    grid-template-columns: 1fr;
  }
}
</style>
