<template>
  <div class="alert-center-page">
    <div class="page-header">
      <div>
        <h1>预警中心</h1>
        <p>支持按权限查看、处理预警，并导出当前筛选结果报表。</p>
      </div>
      <div class="header-actions">
        <el-button @click="handleRefresh">刷新</el-button>
        <el-button type="success" :loading="exportLoading" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出报表
        </el-button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card pending">
        <span class="value">{{ statistics.by_status.pending || 0 }}</span>
        <span class="label">待处理</span>
      </div>
      <div class="stat-card processing">
        <span class="value">{{ statistics.by_status.processing || 0 }}</span>
        <span class="label">处理中</span>
      </div>
      <div class="stat-card resolved">
        <span class="value">{{ statistics.by_status.resolved || 0 }}</span>
        <span class="label">已解决</span>
      </div>
      <div class="stat-card ignored">
        <span class="value">{{ statistics.by_status.ignored || 0 }}</span>
        <span class="label">已忽略</span>
      </div>
    </div>

    <el-card shadow="hover" class="search-card">
      <el-form :inline="true">
        <el-form-item label="学生姓名">
          <el-input v-model="searchForm.student_name" placeholder="请输入学生姓名" clearable />
        </el-form-item>
        <el-form-item label="预警级别">
          <el-select v-model="searchForm.level" placeholder="全部级别" clearable style="width: 140px">
            <el-option label="警告" value="warning" />
            <el-option label="严重" value="serious" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable style="width: 140px">
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
        <el-table-column prop="student_name" label="学生姓名" width="110" />
        <el-table-column prop="student_no" label="学号" width="140" />
        <el-table-column prop="class_name" label="班级" width="140" />
        <el-table-column prop="rule_name" label="预警规则" width="150" />
        <el-table-column prop="message" label="预警信息" min-width="220" show-overflow-tooltip />
        <el-table-column label="级别" width="90">
          <template #default="{ row }">
            <el-tag :type="levelTagMap[row.level] || 'info'">
              {{ levelTextMap[row.level] || row.level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="学生反馈" width="100">
          <template #default="{ row }">
            <el-tag :type="row.student_feedback ? 'success' : 'info'">
              {{ row.student_feedback ? '已提交' : '未提交' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openAlert(row)">
              {{ row.status === 'pending' ? '处理' : '查看' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchAlerts"
          @current-change="fetchAlerts"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEditable ? '预警处理' : '预警详情'"
      width="760px"
      destroy-on-close
    >
      <div v-if="currentAlert" class="dialog-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="学生姓名">{{ currentAlert.student?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="学号">{{ currentAlert.student?.student_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="班级">{{ currentAlert.student?.class_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ currentAlert.student?.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="预警规则">{{ currentAlert.rule?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="规则类型">
            <el-tag :type="ruleTypeTagMap[currentAlert.rule?.type || ''] || 'info'">
              {{ ruleTypeTextMap[currentAlert.rule?.type || ''] || currentAlert.rule?.type || '-' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="风险级别">
            <el-tag :type="levelTagMap[currentAlert.level] || 'info'">
              {{ levelTextMap[currentAlert.level] || currentAlert.level }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="statusTagMap[currentAlert.status] || 'info'">
              {{ statusTextMap[currentAlert.status] || currentAlert.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ formatDate(currentAlert.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(currentAlert.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="规则描述" :span="2">
            {{ currentAlert.rule?.description || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          class="detail-alert"
          :title="currentAlert.message"
          :type="currentAlert.level === 'urgent' ? 'error' : 'warning'"
          show-icon
          :closable="false"
        />

        <el-card shadow="never" class="detail-card" v-if="conditionEntries.length">
          <template #header>触发条件</template>
          <div class="condition-grid">
            <div v-for="item in conditionEntries" :key="item.key" class="condition-item">
              <span class="condition-label">{{ item.label }}</span>
              <span class="condition-value">{{ item.value }}</span>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="detail-card">
          <template #header>学生申诉 / 反馈</template>
          <div v-if="currentAlert.student_feedback" class="feedback-box">
            <div class="feedback-time">提交时间：{{ formatDate(currentAlert.feedback_time) }}</div>
            <div class="feedback-content">{{ currentAlert.student_feedback }}</div>
          </div>
          <el-empty v-else description="学生暂未提交反馈" :image-size="60" />
        </el-card>

        <el-card shadow="never" class="detail-card">
          <template #header>处理记录</template>
          <el-timeline v-if="currentAlert.records?.length">
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
          <el-empty v-else description="暂无处理记录" :image-size="60" />
        </el-card>

        <el-card v-if="isEditable" shadow="never" class="detail-card">
          <template #header>新增处理记录</template>
          <el-form ref="formRef" :model="handleForm" :rules="handleFormRules" label-width="88px">
            <el-form-item label="处理方式" prop="action">
              <el-select v-model="handleForm.action" placeholder="请选择处理方式">
                <el-option label="电话联系" value="电话联系" />
                <el-option label="面谈" value="面谈" />
                <el-option label="微信沟通" value="微信沟通" />
                <el-option label="家长联系" value="家长联系" />
                <el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
            <el-form-item label="更新状态" prop="newStatus">
              <el-select v-model="handleForm.newStatus" placeholder="请选择状态">
                <el-option label="处理中" value="processing" />
                <el-option label="已解决" value="resolved" />
                <el-option label="已忽略" value="ignored" />
              </el-select>
            </el-form-item>
            <el-form-item label="处理说明" prop="result">
              <el-input
                v-model="handleForm.result"
                type="textarea"
                :rows="4"
                maxlength="500"
                show-word-limit
                placeholder="请填写处理经过、与学生沟通结果、后续跟踪安排等。"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button v-if="isEditable" type="primary" :loading="submitLoading" @click="submitHandle">
          提交处理
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

import { getAlert, getAlerts, getAlertStatistics, handleAlert, updateAlertStatus } from '@/api/alert'
import type { AlertLevel, AlertStatus } from '@/types'
import { request } from '@/utils/request'

type TagType = 'success' | 'warning' | 'primary' | 'info' | 'danger'

type AlertListItem = {
  id: number
  student_name?: string
  student_no?: string
  class_name?: string
  rule_name?: string
  level: AlertLevel
  message: string
  status: AlertStatus
  student_feedback?: string | null
  feedback_time?: string | null
  created_at: string
}

type AlertDetailData = AlertListItem & {
  updated_at?: string
  student?: {
    name?: string
    student_no?: string
    class_name?: string
    phone?: string
  }
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
const submitLoading = ref(false)
const exportLoading = ref(false)
const dialogVisible = ref(false)
const alerts = ref<AlertListItem[]>([])
const currentAlert = ref<AlertDetailData | null>(null)
const formRef = ref<FormInstance>()

const statistics = reactive({
  total: 0,
  by_status: {
    pending: 0,
    processing: 0,
    resolved: 0,
    ignored: 0
  },
  by_level: {
    warning: 0,
    serious: 0,
    urgent: 0
  }
})

const searchForm = reactive({
  student_name: '',
  level: undefined as AlertLevel | undefined,
  status: undefined as AlertStatus | undefined
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const handleForm = reactive({
  action: '',
  result: '',
  newStatus: 'processing' as AlertStatus
})

const handleFormRules: FormRules = {
  action: [{ required: true, message: '请选择处理方式', trigger: 'change' }],
  result: [{ required: true, message: '请填写处理说明', trigger: 'blur' }],
  newStatus: [{ required: true, message: '请选择更新状态', trigger: 'change' }]
}

const levelTextMap: Record<string, string> = {
  warning: '警告',
  serious: '严重',
  urgent: '紧急'
}

const levelTagMap: Record<string, TagType> = {
  warning: 'warning',
  serious: 'danger',
  urgent: 'danger'
}

const statusTextMap: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  ignored: '已忽略'
}

const statusTagMap: Record<string, TagType> = {
  pending: 'warning',
  processing: 'danger',
  resolved: 'success',
  ignored: 'info'
}

const ruleTypeTextMap: Record<string, string> = {
  score: '成绩预警',
  attendance: '考勤预警',
  graduation: '学分/毕业风险',
  comprehensive: '综合风险'
}

const ruleTypeTagMap: Record<string, TagType> = {
  score: 'danger',
  attendance: 'warning',
  graduation: 'info',
  comprehensive: 'primary'
}

const isEditable = computed(() => {
  return currentAlert.value?.status === 'pending' || currentAlert.value?.status === 'processing'
})

const conditionEntries = computed(() => {
  const conditions = currentAlert.value?.rule?.conditions || {}
  const labelMap: Record<string, string> = {
    metric: '指标',
    operator: '运算符',
    threshold: '阈值',
    time_window: '时间窗口',
    fail_count_threshold: '挂科门数阈值',
    absence_count_threshold: '缺勤次数阈值',
    mode: '规则模式'
  }

  return Object.entries(conditions)
    .filter(([, value]) => value !== null && value !== undefined && value !== '')
    .map(([key, value]) => ({
      key,
      label: labelMap[key] || key,
      value: String(value)
    }))
})

function formatDate(value?: string | null) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function buildQueryParams() {
  return {
    page: pagination.page,
    page_size: pagination.pageSize,
    student_name: searchForm.student_name || undefined,
    level: searchForm.level,
    status: searchForm.status
  }
}

async function fetchStatistics() {
  try {
    const response = await getAlertStatistics()
    statistics.total = response.total || 0
    statistics.by_status = { ...statistics.by_status, ...(response.by_status || {}) }
    statistics.by_level = { ...statistics.by_level, ...(response.by_level || {}) }
  } catch (error) {
    console.error('加载统计失败', error)
  }
}

async function fetchAlerts() {
  loading.value = true
  try {
    const response = await getAlerts(buildQueryParams())
    alerts.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    console.error('加载预警列表失败', error)
    ElMessage.error('加载预警列表失败')
  } finally {
    loading.value = false
  }
}

async function openAlert(row: AlertListItem) {
  try {
    const detail = await getAlert(row.id)
    currentAlert.value = detail as unknown as AlertDetailData
    handleForm.action = ''
    handleForm.result = ''
    handleForm.newStatus = detail.status === 'pending' ? ('processing' as AlertStatus) : (detail.status as AlertStatus)
    dialogVisible.value = true
  } catch (error) {
    console.error('加载预警详情失败', error)
    ElMessage.error('加载预警详情失败')
  }
}

async function submitHandle() {
  if (!currentAlert.value || !formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    await handleAlert(currentAlert.value.id, {
      action: handleForm.action,
      result: handleForm.result
    })

    if (handleForm.newStatus !== currentAlert.value.status) {
      await updateAlertStatus(currentAlert.value.id, handleForm.newStatus)
    }

    ElMessage.success('预警处理已保存')
    dialogVisible.value = false
    await Promise.all([fetchAlerts(), fetchStatistics()])
  } catch (error) {
    console.error('提交处理失败', error)
    ElMessage.error('提交处理失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleExport() {
  exportLoading.value = true
  try {
    const blob = await request.get<Blob>('/alerts/export', {
      params: {
        student_name: searchForm.student_name || undefined,
        level: searchForm.level,
        status: searchForm.status
      },
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `学业预警报表_${dayjs().format('YYYY-MM-DD')}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('报表导出成功')
  } catch (error) {
    console.error('导出报表失败', error)
    ElMessage.error('导出报表失败')
  } finally {
    exportLoading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchAlerts()
}

function handleReset() {
  searchForm.student_name = ''
  searchForm.level = undefined
  searchForm.status = undefined
  pagination.page = 1
  fetchAlerts()
}

function handleRefresh() {
  fetchStatistics()
  fetchAlerts()
}

onMounted(() => {
  handleRefresh()
})
</script>

<style scoped lang="scss">
.alert-center-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 20px;

  h1 {
    margin: 0 0 8px;
    font-size: 24px;
    font-weight: 700;
  }

  p {
    margin: 0;
    color: var(--el-text-color-secondary);
  }
}

.header-actions {
  display: flex;
  gap: 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  border-radius: 12px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: #fff;

  .value {
    font-size: 30px;
    font-weight: 700;
  }

  .label {
    font-size: 14px;
    opacity: 0.9;
  }

  &.pending {
    background: linear-gradient(135deg, #f6ad55, #ed8936);
  }

  &.processing {
    background: linear-gradient(135deg, #fc8181, #f56565);
  }

  &.resolved {
    background: linear-gradient(135deg, #68d391, #38a169);
  }

  &.ignored {
    background: linear-gradient(135deg, #a0aec0, #718096);
  }
}

.search-card {
  margin-bottom: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-alert {
  margin-top: 4px;
}

.detail-card {
  margin-top: 0;
}

.condition-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.condition-item {
  background: #f7fafc;
  border-radius: 8px;
  padding: 12px;
}

.condition-label {
  display: block;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}

.condition-value {
  font-weight: 600;
}

.feedback-time {
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

@media (max-width: 960px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .page-header {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
  }

  .stats-grid,
  .condition-grid {
    grid-template-columns: 1fr;
  }
}
</style>
