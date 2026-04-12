<template>
  <div class="student-alerts-page">
    <div class="page-header">
      <div>
        <h2>我的预警</h2>
        <p>查看预警详情、处理进度，并可提交个人申诉或情况说明。</p>
      </div>
      <el-button @click="loadAlerts">刷新</el-button>
    </div>

    <div class="stats-grid">
      <el-card shadow="hover" class="stat-card total">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">预警总数</div>
      </el-card>
      <el-card shadow="hover" class="stat-card high">
        <div class="stat-value">{{ stats.high }}</div>
        <div class="stat-label">高风险</div>
      </el-card>
      <el-card shadow="hover" class="stat-card medium">
        <div class="stat-value">{{ stats.medium }}</div>
        <div class="stat-label">中风险</div>
      </el-card>
      <el-card shadow="hover" class="stat-card low">
        <div class="stat-value">{{ stats.low }}</div>
        <div class="stat-label">低风险</div>
      </el-card>
    </div>

    <el-card shadow="hover" class="filter-card">
      <el-form :inline="true">
        <el-form-item label="预警类型">
          <el-select v-model="filters.type" clearable placeholder="全部类型" style="width: 160px">
            <el-option label="成绩预警" value="grade" />
            <el-option label="考勤预警" value="attendance" />
            <el-option label="学分预警" value="credit" />
            <el-option label="综合风险" value="comprehensive" />
          </el-select>
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="filters.level" clearable placeholder="全部等级" style="width: 140px">
            <el-option label="高风险" value="high" />
            <el-option label="中风险" value="medium" />
            <el-option label="低风险" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理状态">
          <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 140px">
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已忽略" value="ignored" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover">
      <el-table :data="alerts" v-loading="loading" stripe>
        <el-table-column prop="alert_type" label="预警类型" width="120">
          <template #default="{ row }">
            <el-tag :type="typeTagMap[row.alert_type] || 'info'">
              {{ typeTextMap[row.alert_type] || row.alert_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alert_level" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="levelTagMap[row.alert_level] || 'info'">
              {{ levelTextMap[row.alert_level] || row.alert_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="预警描述" min-width="220" show-overflow-tooltip />
        <el-table-column prop="suggestion" label="建议措施" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.suggestion || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="反馈状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.student_feedback ? 'success' : 'warning'">
              {{ row.student_feedback ? '已反馈' : '待反馈' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="处理状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagMap[row.status] || 'info'">
              {{ statusTextMap[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadAlerts"
          @current-change="loadAlerts"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="预警详情" width="760px" destroy-on-close>
      <div v-loading="detailLoading">
        <template v-if="currentAlert">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="预警类型">
              <el-tag :type="typeTagMap[currentAlert.rule?.type || currentAlert.alert_type] || 'info'">
                {{ typeTextMap[currentAlert.rule?.type || currentAlert.alert_type] || currentAlert.rule?.type || currentAlert.alert_type }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="风险等级">
              <el-tag :type="levelTagMap[currentAlert.alert_level] || 'info'">
                {{ levelTextMap[currentAlert.alert_level] || currentAlert.alert_level }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="处理状态">
              <el-tag :type="statusTagMap[currentAlert.status] || 'info'">
                {{ statusTextMap[currentAlert.status] || currentAlert.status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="生成时间">
              {{ formatDate(currentAlert.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">
              {{ formatDate(currentAlert.updated_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="学期" v-if="currentAlert.semester">
              {{ currentAlert.semester }}
            </el-descriptions-item>
            <el-descriptions-item label="预警规则" :span="2">
              {{ currentAlert.rule?.name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="规则描述" :span="2">
              {{ currentAlert.rule?.description || currentAlert.suggestion || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <el-alert
            class="detail-alert"
            :title="currentAlert.message"
            :type="currentAlert.alert_level === 'high' ? 'error' : 'warning'"
            :closable="false"
            show-icon
          />

          <el-card shadow="never" class="feedback-card">
            <template #header>
              <div class="card-header">
                <span>学生申诉 / 反馈</span>
                <el-tag :type="hasFeedback ? 'success' : 'warning'">
                  {{ hasFeedback ? '已提交' : '未提交' }}
                </el-tag>
              </div>
            </template>

            <div v-if="hasFeedback" class="feedback-result">
              <div class="feedback-meta">提交时间：{{ formatDate(currentAlert.feedback_time) }}</div>
              <div class="feedback-content">{{ currentAlert.student_feedback }}</div>
            </div>
            <div v-else class="feedback-form">
              <el-input
                v-model="feedbackForm.feedback"
                type="textarea"
                :rows="5"
                maxlength="1000"
                show-word-limit
                placeholder="例如：老师，我上周因住院治疗导致缺勤，相关材料可补充提交。"
              />
              <div class="feedback-actions">
                <el-button
                  type="primary"
                  :loading="feedbackLoading"
                  :disabled="!feedbackForm.feedback.trim()"
                  @click="submitFeedback"
                >
                  提交反馈
                </el-button>
              </div>
            </div>
          </el-card>

          <el-card v-if="currentAlert.records?.length" shadow="never" class="record-card">
            <template #header>辅导处理记录</template>
            <el-timeline>
              <el-timeline-item
                v-for="record in currentAlert.records"
                :key="record.id"
                :timestamp="formatDate(record.created_at)"
              >
                <div class="record-title">{{ record.action }}</div>
                <div class="record-meta">{{ record.handler_name || '系统' }}</div>
                <div class="record-content">{{ record.result || '暂无详细说明' }}</div>
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </template>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'

import { getStudentAlerts } from '@/api/student'
import { request } from '@/utils/request'

type TagType = 'success' | 'warning' | 'primary' | 'info' | 'danger'

type StudentAlertItem = {
  id: number
  alert_type: 'grade' | 'attendance' | 'credit' | 'comprehensive'
  alert_level: 'high' | 'medium' | 'low'
  description: string
  suggestion?: string
  status: 'pending' | 'processing' | 'resolved' | 'ignored'
  student_feedback?: string | null
  feedback_time?: string | null
  created_at: string
  updated_at?: string
}

type StudentAlertDetail = StudentAlertItem & {
  message: string
  semester?: string | null
  rule?: {
    name?: string
    type?: string
    description?: string
    conditions?: Record<string, unknown>
  }
  records?: Array<{
    id: number
    action: string
    result?: string
    handler_name?: string
    created_at: string
  }>
}

const loading = ref(false)
const detailLoading = ref(false)
const feedbackLoading = ref(false)
const detailVisible = ref(false)

const alerts = ref<StudentAlertItem[]>([])
const currentAlert = ref<StudentAlertDetail | null>(null)
const stats = reactive({
  total: 0,
  high: 0,
  medium: 0,
  low: 0
})

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

const feedbackForm = reactive({
  feedback: ''
})

const typeTextMap: Record<string, string> = {
  grade: '成绩预警',
  attendance: '考勤预警',
  credit: '学分预警',
  comprehensive: '综合风险',
  score: '成绩预警',
  graduation: '学分预警'
}

const typeTagMap: Record<string, TagType> = {
  grade: 'danger',
  attendance: 'warning',
  credit: 'info',
  comprehensive: 'primary',
  score: 'danger',
  graduation: 'info'
}

const levelTextMap: Record<string, string> = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
  urgent: '高风险',
  serious: '中风险',
  warning: '低风险'
}

const levelTagMap: Record<string, TagType> = {
  high: 'danger',
  medium: 'warning',
  low: 'info',
  urgent: 'danger',
  serious: 'warning',
  warning: 'info'
}

const statusTextMap: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  ignored: '已忽略'
}

const statusTagMap: Record<string, TagType> = {
  pending: 'danger',
  processing: 'warning',
  resolved: 'success',
  ignored: 'info'
}

const hasFeedback = computed(() => Boolean(currentAlert.value?.student_feedback?.trim()))

function formatDate(value?: string | null) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function normalizeAlertLevel(value?: string) {
  if (value === 'urgent') return 'high'
  if (value === 'serious') return 'medium'
  if (value === 'warning') return 'low'
  return value || 'low'
}

async function loadAlerts() {
  loading.value = true
  try {
    const response = await getStudentAlerts({
      page: pagination.page,
      page_size: pagination.pageSize,
      type: filters.type || undefined,
      level: filters.level || undefined,
      status: filters.status || undefined
    })

    alerts.value = (response.items || []).map((item) => ({
      ...item,
      alert_level: normalizeAlertLevel(item.alert_level) as StudentAlertItem['alert_level']
    }))
    pagination.total = response.total || 0

    stats.total = response.stats?.total || 0
    stats.high = response.stats?.high || 0
    stats.medium = response.stats?.medium || 0
    stats.low = response.stats?.low || 0
  } catch (error) {
    console.error('加载预警失败', error)
    ElMessage.error('加载预警失败')
  } finally {
    loading.value = false
  }
}

async function openDetail(row: StudentAlertItem) {
  detailVisible.value = true
  detailLoading.value = true
  feedbackForm.feedback = ''
  try {
    const detail = await request.get<any>(`/alerts/${row.id}`)
    currentAlert.value = {
      ...detail,
      alert_type: row.alert_type,
      alert_level: normalizeAlertLevel(detail.level || row.alert_level) as StudentAlertItem['alert_level']
    }
  } catch (error) {
    console.error('加载预警详情失败', error)
    ElMessage.error('加载预警详情失败')
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

async function submitFeedback() {
  if (!currentAlert.value) return

  const feedback = feedbackForm.feedback.trim()
  if (!feedback) {
    ElMessage.warning('请先填写反馈内容')
    return
  }

  feedbackLoading.value = true
  try {
    await request.post(`/alerts/${currentAlert.value.id}/feedback`, { feedback })
    ElMessage.success('反馈提交成功')
    await openDetail(currentAlert.value)
    await loadAlerts()
  } catch (error) {
    console.error('提交反馈失败', error)
    ElMessage.error('提交反馈失败')
  } finally {
    feedbackLoading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadAlerts()
}

function handleReset() {
  filters.type = ''
  filters.level = ''
  filters.status = ''
  pagination.page = 1
  loadAlerts()
}

onMounted(() => {
  loadAlerts()
})
</script>

<style scoped lang="scss">
.student-alerts-page {
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
  }

  p {
    margin: 0;
    color: var(--el-text-color-secondary);
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  .stat-value {
    font-size: 28px;
    font-weight: 700;
  }

  .stat-label {
    margin-top: 8px;
    color: var(--el-text-color-secondary);
  }

  &.total {
    border-top: 3px solid #409eff;
  }

  &.high {
    border-top: 3px solid #f56c6c;
  }

  &.medium {
    border-top: 3px solid #e6a23c;
  }

  &.low {
    border-top: 3px solid #909399;
  }
}

.filter-card {
  margin-bottom: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-alert {
  margin-top: 16px;
}

.feedback-card,
.record-card {
  margin-top: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feedback-meta {
  color: var(--el-text-color-secondary);
  margin-bottom: 10px;
}

.feedback-content {
  white-space: pre-wrap;
  line-height: 1.8;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 14px;
}

.feedback-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.record-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.record-meta {
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}

.record-content {
  line-height: 1.7;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .page-header {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
