<template>
  <div class="student-overview">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>个人概览</h2>
      <p class="subtitle">查看您的学业数据统计和预警信息</p>
    </div>

    <!-- 个人信息卡片 -->
    <el-card class="info-card" shadow="hover">
      <div class="student-info">
        <el-avatar :size="80" :src="avatarUrl">
          {{ studentInfo?.name?.charAt(0) }}
        </el-avatar>
        <div class="info-content">
          <h3>{{ studentInfo?.name }}</h3>
          <div class="info-details">
            <span><el-icon><User /></el-icon> 学号：{{ studentInfo?.student_no }}</span>
            <span><el-icon><School /></el-icon> 班级：{{ studentInfo?.class_name }}</span>
            <span><el-icon><Phone /></el-icon> 联系方式：{{ studentInfo?.phone || '未填写' }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card grade-card">
          <div class="stat-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.avgScore || '--' }}</div>
            <div class="stat-label">平均绩点</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card attendance-card">
          <div class="stat-icon">
            <el-icon><Calendar /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.attendanceRate || '--' }}%</div>
            <div class="stat-label">出勤率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card alert-card">
          <div class="stat-icon">
            <el-icon><Warning /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.alertCount || 0 }}</div>
            <div class="stat-label">预警数量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card credit-card">
          <div class="stat-icon">
            <el-icon><Medal /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.earnedCredits || '--' }}</div>
            <div class="stat-label">已获学分</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近预警 -->
    <el-card class="recent-alerts" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>最近预警</span>
          <el-button type="primary" link @click="$router.push('/student/my-alerts')">
            查看全部
          </el-button>
        </div>
      </template>
      <el-table :data="recentAlerts" style="width: 100%" v-if="recentAlerts.length > 0">
        <el-table-column prop="alert_type" label="预警类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getAlertTagType(row.alert_type)">
              {{ getAlertTypeName(row.alert_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alert_level" label="预警等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getLevelTagType(row.alert_level)" effect="dark">
              {{ getLevelName(row.alert_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无预警信息" :image-size="100" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { TrendCharts, Calendar, Warning, Medal, User, School, Phone } from '@element-plus/icons-vue'
import { getStudentStats, getStudentAlerts } from '@/api/student'
import { getUserProfile } from '@/api/auth'
import type { UserProfile } from '@/types'

const userStore = useUserStore()
const userProfile = ref<UserProfile | null>(null)

interface StudentInfo {
  name: string
  student_no: string
  class_name: string
  phone?: string
  avatar?: string
}

interface Stats {
  avgScore: number
  attendanceRate: number
  alertCount: number
  earnedCredits: number
}

const studentInfo = ref<StudentInfo | null>(null)
const stats = ref<Stats>({
  avgScore: 0,
  attendanceRate: 0,
  alertCount: 0,
  earnedCredits: 0
})
const recentAlerts = ref<any[]>([])

// 头像URL（与Header.vue保持一致）
const avatarUrl = computed(() => {
  if (userProfile.value?.avatar_url) {
    if (userProfile.value.avatar_url.startsWith('/')) {
      return `http://localhost:8000${userProfile.value.avatar_url}`
    }
    return userProfile.value.avatar_url
  }
  return ''
})

// 获取预警类型名称
const getAlertTypeName = (type: string) => {
  const map: Record<string, string> = {
    grade: '成绩预警',
    attendance: '考勤预警',
    credit: '学分预警',
    comprehensive: '综合预警'
  }
  return map[type] || type
}

// 获取预警类型标签颜色
const getAlertTagType = (type: string) => {
  const map: Record<string, string> = {
    grade: 'danger',
    attendance: 'warning',
    credit: 'info',
    comprehensive: ''
  }
  return map[type] || ''
}

// 获取预警等级名称
const getLevelName = (level: string) => {
  const map: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高'
  }
  return map[level] || level
}

// 获取预警等级标签颜色
const getLevelTagType = (level: string) => {
  const map: Record<string, string> = {
    low: 'info',
    medium: 'warning',
    high: 'danger'
  }
  return map[level] || 'info'
}

// 格式化日期
const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 加载数据
const loadData = async () => {
  // 从用户信息获取学生基本信息
  const user = userStore.userInfo
  if (user?.student) {
    studentInfo.value = {
      name: user.student.name,
      student_no: user.student.student_no,
      class_name: user.student.class_name || '未分配',
      phone: user.student.phone,
      avatar: user.student.avatar
    }
  }

  try {
    // 获取用户详细信息（包含头像，与Header.vue保持一致）
    userProfile.value = await getUserProfile()

    // 获取统计数据
    const statsRes = await getStudentStats()
    stats.value = statsRes

    // 获取最近预警
    const alertsRes = await getStudentAlerts({ page: 1, page_size: 5 })
    recentAlerts.value = alertsRes.items || []
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.student-overview {
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

  .info-card {
    margin-bottom: 20px;

    .student-info {
      display: flex;
      align-items: center;
      gap: 24px;

      .info-content {
        h3 {
          margin: 0 0 12px 0;
          font-size: 20px;
        }

        .info-details {
          display: flex;
          flex-wrap: wrap;
          gap: 20px;
          color: var(--el-text-color-secondary);

          span {
            display: flex;
            align-items: center;
            gap: 6px;
          }
        }
      }
    }
  }

  .stat-cards {
    margin-bottom: 20px;

    .stat-card {
      display: flex;
      align-items: center;
      padding: 20px;

      .stat-icon {
        width: 60px;
        height: 60px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        color: #fff;
        margin-right: 16px;
      }

      .stat-content {
        .stat-value {
          font-size: 28px;
          font-weight: 600;
          line-height: 1.2;
        }

        .stat-label {
          font-size: 14px;
          color: var(--el-text-color-secondary);
        }
      }

      &.grade-card .stat-icon {
        background: linear-gradient(135deg, #667eea, #764ba2);
      }

      &.attendance-card .stat-icon {
        background: linear-gradient(135deg, #11998e, #38ef7d);
      }

      &.alert-card .stat-icon {
        background: linear-gradient(135deg, #f093fb, #f5576c);
      }

      &.credit-card .stat-icon {
        background: linear-gradient(135deg, #4facfe, #00f2fe);
      }
    }
  }

  .recent-alerts {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}

@media (max-width: 768px) {
  .student-overview {
    .info-card .student-info {
      flex-direction: column;
      text-align: center;

      .info-details {
        justify-content: center;
      }
    }

    .stat-cards .stat-card {
      margin-bottom: 12px;
    }
  }
}
</style>
