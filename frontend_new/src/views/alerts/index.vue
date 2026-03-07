<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">预警中心</h1>
      <el-button type="primary" @click="handleRefresh">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-row">
      <div class="mini-stat pending">
        <span class="count">{{ statistics.by_status?.pending || 0 }}</span>
        <span class="label">待处理</span>
      </div>
      <div class="mini-stat processing">
        <span class="count">{{ statistics.by_status?.processing || 0 }}</span>
        <span class="label">处理中</span>
      </div>
      <div class="mini-stat resolved">
        <span class="count">{{ statistics.by_status?.resolved || 0 }}</span>
        <span class="label">已解决</span>
      </div>
    </div>

    <!-- 搜索表单 -->
    <div class="search-form card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="学生姓名">
          <el-input v-model="searchForm.student_name" placeholder="请输入学生姓名" clearable />
        </el-form-item>
        <el-form-item label="预警级别">
          <el-select v-model="searchForm.level" placeholder="请选择级别" clearable>
            <el-option label="警告" value="warning" />
            <el-option label="严重" value="serious" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态" clearable>
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已忽略" value="ignored" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 表格 -->
    <div class="page-content">
      <el-table :data="alerts" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="student_name" label="学生姓名" width="100" />
        <el-table-column prop="student_no" label="学号" width="130" />
        <el-table-column prop="class_name" label="班级" width="130" />
        <el-table-column prop="rule_name" label="预警规则" width="120" />
        <el-table-column prop="message" label="预警信息" show-overflow-tooltip />
        <el-table-column label="级别" width="80">
          <template #default="{ row }">
            <span :class="['level-tag', row.level]">{{ levelText[row.level] }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType[row.status]" size="small">
              {{ statusText[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              type="primary"
              link
              size="small"
              @click="viewAlert(row)"
            >
              处理
            </el-button>
            <el-button
              v-else
              type="primary"
              link
              size="small"
              @click="viewAlert(row)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchAlerts"
          @current-change="fetchAlerts"
        />
      </div>
    </div>

    <!-- 处理对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isPending ? '预警处理' : '预警详情'"
      width="700px"
      destroy-on-close
    >
      <div v-if="currentAlert" class="alert-detail">
        <!-- 学生基本信息 -->
        <el-divider content-position="left">
          <el-icon><User /></el-icon>
          学生信息
        </el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="学生姓名">
            <span class="highlight">{{ currentAlert.student?.name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="学号">{{ currentAlert.student?.student_no }}</el-descriptions-item>
          <el-descriptions-item label="班级">{{ currentAlert.student?.class_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ currentAlert.student?.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="电子邮箱" :span="2">{{ currentAlert.student?.email || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 预警规则详情 -->
        <el-divider content-position="left">
          <el-icon><Warning /></el-icon>
          触发规则
        </el-divider>
        <div class="rule-detail">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="规则名称">
              <el-tag type="info" size="small">{{ currentAlert.rule?.name }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="规则编码">{{ currentAlert.rule?.code }}</el-descriptions-item>
            <el-descriptions-item label="规则类型">
              <el-tag :type="ruleTypeTag[currentAlert.rule?.type || '']" size="small">
                {{ ruleTypeText[currentAlert.rule?.type || ''] }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="预警级别">
              <span :class="['level-tag', currentAlert.level]">
                {{ levelText[currentAlert.level] }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="规则描述" :span="2">
              {{ currentAlert.rule?.description || '暂无描述' }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- 触发条件 -->
          <div class="condition-box" v-if="currentAlert.rule?.conditions">
            <div class="condition-title">
              <el-icon><Document /></el-icon>
              触发条件详情
            </div>
            <div class="condition-content">
              <template v-for="(value, key) in currentAlert.rule.conditions" :key="key">
                <div class="condition-item" v-if="value !== null && value !== ''">
                  <span class="condition-label">{{ getConditionLabel(key) }}:</span>
                  <span class="condition-value">{{ formatConditionValue(key, value) }}</span>
                </div>
              </template>
            </div>
          </div>
        </div>

        <!-- 预警信息 -->
        <el-divider content-position="left">
          <el-icon><Bell /></el-icon>
          预警信息
        </el-divider>
        <el-alert
          :title="currentAlert.message"
          :type="alertTypeMap[currentAlert.level]"
          show-icon
          :closable="false"
          class="alert-message"
        />
        <div class="alert-meta">
          <span>生成时间: {{ formatDate(currentAlert.created_at) }}</span>
          <span>当前状态:
            <el-tag :type="statusType[currentAlert.status]" size="small">
              {{ statusText[currentAlert.status] }}
            </el-tag>
          </span>
        </div>

        <!-- 处理记录 -->
        <el-divider content-position="left">
          <el-icon><Clock /></el-icon>
          处理记录
        </el-divider>
        <el-timeline v-if="currentAlert.records?.length" class="record-timeline">
          <el-timeline-item
            v-for="record in currentAlert.records"
            :key="record.id"
            :timestamp="formatDate(record.created_at)"
            placement="top"
            type="primary"
          >
            <el-card shadow="never" class="record-card">
              <div class="record-item">
                <div class="record-header">
                  <span class="handler">
                    <el-icon><User /></el-icon>
                    {{ record.handler_name }}
                  </span>
                  <el-tag size="small" type="info">{{ record.action }}</el-tag>
                </div>
                <div class="record-result" v-if="record.result">{{ record.result }}</div>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无处理记录" :image-size="60" />

        <!-- 添加处理记录表单 -->
        <template v-if="isPending || currentAlert.status === 'processing'">
          <el-divider content-position="left">
            <el-icon><Edit /></el-icon>
            添加处理记录
          </el-divider>
          <el-form
            ref="handleFormRef"
            :model="handleForm"
            :rules="handleFormRules"
            label-width="100px"
            class="handle-form"
          >
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="处理方式" prop="action">
                  <el-select v-model="handleForm.action" placeholder="请选择处理方式" style="width: 100%">
                    <el-option label="电话联系" value="电话联系">
                      <el-icon><Phone /></el-icon> 电话联系
                    </el-option>
                    <el-option label="面谈" value="面谈">
                      <el-icon><ChatDotRound /></el-icon> 面谈
                    </el-option>
                    <el-option label="微信联系" value="微信联系">
                      <el-icon><ChatRound /></el-icon> 微信联系
                    </el-option>
                    <el-option label="邮件联系" value="邮件联系">
                      <el-icon><Message /></el-icon> 邮件联系
                    </el-option>
                    <el-option label="家长沟通" value="家长沟通">
                      <el-icon><User /></el-icon> 家长沟通
                    </el-option>
                    <el-option label="其他" value="其他">
                      <el-icon><More /></el-icon> 其他
                    </el-option>
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="更改状态" prop="newStatus">
                  <el-select v-model="handleForm.newStatus" placeholder="请选择状态" style="width: 100%">
                    <el-option label="处理中" value="processing">
                      <el-tag type="danger" size="small">处理中</el-tag>
                    </el-option>
                    <el-option label="已解决" value="resolved">
                      <el-tag type="success" size="small">已解决</el-tag>
                    </el-option>
                    <el-option label="已忽略" value="ignored">
                      <el-tag type="info" size="small">已忽略</el-tag>
                    </el-option>
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="跟进记录" prop="result">
              <el-input
                v-model="handleForm.result"
                type="textarea"
                :rows="4"
                placeholder="请详细描述处理情况，如：已与学生面谈，学生承诺改进学习态度，后续将持续关注..."
                maxlength="500"
                show-word-limit
              />
            </el-form-item>
          </el-form>
        </template>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">关闭</el-button>
          <template v-if="isPending || currentAlert?.status === 'processing'">
            <el-button
              type="primary"
              :loading="submitLoading"
              @click="submitHandle"
            >
              <el-icon><Check /></el-icon>
              提交处理
            </el-button>
          </template>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import {
  Refresh, User, Warning, Bell, Clock, Edit, Check,
  Phone, ChatDotRound, ChatRound, Message, More, Document
} from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import dayjs from 'dayjs'
import { getAlerts, getAlert, getAlertStatistics, handleAlert, updateAlertStatus } from '@/api/alert'
import type { Alert, AlertDetail, AlertLevel, AlertStatus } from '@/types'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const alerts = ref<Alert[]>([])
const currentAlert = ref<AlertDetail | null>(null)
const handleFormRef = ref<FormInstance>()

const statistics = ref({
  total: 0,
  by_status: {} as Record<string, number>,
  by_level: {} as Record<string, number>
})

const searchForm = reactive({
  student_name: '',
  level: undefined as AlertLevel | undefined,
  status: undefined as AlertStatus | undefined
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const handleForm = reactive({
  action: '',
  result: '',
  newStatus: 'processing' as AlertStatus
})

// 表单验证规则
const handleFormRules: FormRules = {
  action: [{ required: true, message: '请选择处理方式', trigger: 'change' }],
  newStatus: [{ required: true, message: '请选择状态', trigger: 'change' }],
  result: [{ required: true, message: '请填写跟进记录', trigger: 'blur' }]
}

// 文本映射
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
const ruleTypeText: Record<string, string> = {
  score: '成绩预警',
  attendance: '考勤预警',
  graduation: '毕业风险'
}
const ruleTypeTag: Record<string, string> = {
  score: 'danger',
  attendance: 'warning',
  graduation: 'info'
}
const alertTypeMap: Record<string, 'warning' | 'error' | 'info'> = {
  warning: 'warning',
  serious: 'warning',
  urgent: 'error'
}

// 是否为待处理状态
const isPending = computed(() => currentAlert.value?.status === 'pending')

// 条件字段标签映射
const conditionLabels: Record<string, string> = {
  min_score: '最低成绩',
  max_score: '最高成绩',
  avg_score: '平均成绩',
  fail_count: '挂科数量',
  absent_count: '缺勤次数',
  absent_rate: '缺勤率',
  late_count: '迟到次数',
  credit_threshold: '学分阈值',
  required_credits: '必修学分',
  total_credits: '总学分',
  semester: '学期',
  days: '天数'
}

// 获取条件标签
function getConditionLabel(key: string): string {
  return conditionLabels[key] || key
}

// 格式化条件值
function formatConditionValue(key: string, value: any): string {
  if (key.includes('rate') || key.includes('_rate')) {
    return `${value}%`
  }
  if (key.includes('score')) {
    return `${value}分`
  }
  if (key.includes('count')) {
    return `${value}次`
  }
  if (key.includes('credit')) {
    return `${value}学分`
  }
  return String(value)
}

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

async function fetchStatistics() {
  try {
    const res = await getAlertStatistics()
    statistics.value = res
  } catch (error) {
    console.error('获取统计失败', error)
  }
}

async function fetchAlerts() {
  loading.value = true
  try {
    const res = await getAlerts({
      page: pagination.page,
      page_size: pagination.page_size,
      ...searchForm
    })
    alerts.value = res.items
    pagination.total = res.total
  } catch (error) {
    console.error('获取预警列表失败', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchAlerts()
}

function handleReset() {
  Object.assign(searchForm, { student_name: '', level: undefined, status: undefined })
  handleSearch()
}

function handleRefresh() {
  fetchStatistics()
  fetchAlerts()
}

async function viewAlert(alert: Alert) {
  try {
    const res = await getAlert(alert.id)
    currentAlert.value = res

    // 根据当前状态设置默认新状态
    if (res.status === 'pending') {
      handleForm.newStatus = 'processing'
    } else {
      handleForm.newStatus = res.status as AlertStatus
    }

    handleForm.action = ''
    handleForm.result = ''
    dialogVisible.value = true
  } catch (error) {
    console.error('获取预警详情失败', error)
    ElMessage.error('获取预警详情失败')
  }
}

async function submitHandle() {
  if (!currentAlert.value) return

  const valid = await handleFormRef.value?.validate()
  if (!valid) return

  submitLoading.value = true
  try {
    // 1. 添加处理记录
    await handleAlert(currentAlert.value.id, {
      action: handleForm.action,
      result: handleForm.result
    })

    // 2. 更新状态（如果状态有变化）
    if (handleForm.newStatus !== currentAlert.value.status) {
      await updateAlertStatus(currentAlert.value.id, handleForm.newStatus)
    }

    ElMessage.success('处理记录已保存')
    dialogVisible.value = false
    fetchAlerts()
    fetchStatistics()
  } catch (error) {
    console.error('提交失败', error)
    ElMessage.error('提交失败，请重试')
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  fetchStatistics()
  fetchAlerts()
})
</script>

<style lang="scss" scoped>
.page-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  .page-title {
    margin: 0;
    font-size: 22px;
    font-weight: 600;
  }
}

.stat-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.mini-stat {
  flex: 1;
  padding: 20px;
  border-radius: 8px;
  text-align: center;

  .count {
    display: block;
    font-size: 32px;
    font-weight: 600;
  }

  .label {
    color: #fff;
    opacity: 0.9;
    font-size: 14px;
  }

  &.pending { background: linear-gradient(135deg, #E6A23C, #f3d19e); color: #fff; }
  &.processing { background: linear-gradient(135deg, #F56C6C, #fab6b6); color: #fff; }
  &.resolved { background: linear-gradient(135deg, #67C23A, #95d475); color: #fff; }
}

.search-form {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.page-content {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

.level-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;

  &.warning { background: rgba(230, 162, 60, 0.15); color: #E6A23C; }
  &.serious { background: rgba(245, 108, 108, 0.15); color: #F56C6C; }
  &.urgent { background: rgba(245, 108, 108, 0.2); color: #F56C6C; font-weight: 600; }
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

// 预警详情样式
.alert-detail {
  .highlight {
    font-weight: 600;
    color: var(--el-color-primary);
  }

  :deep(.el-divider__text) {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    color: #303133;
  }
}

.rule-detail {
  margin-top: 10px;
}

.condition-box {
  margin-top: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;

  .condition-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    margin-bottom: 12px;
    color: #606266;
  }

  .condition-content {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .condition-item {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    background: #fff;
    border-radius: 6px;

    .condition-label {
      color: #909399;
      margin-right: 8px;
      font-size: 13px;
    }

    .condition-value {
      color: #303133;
      font-weight: 500;
      font-size: 13px;
    }
  }
}

.alert-message {
  margin-bottom: 12px;
}

.alert-meta {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #909399;
}

.record-timeline {
  padding: 10px 0;

  .record-card {
    :deep(.el-card__body) {
      padding: 12px 16px;
    }
  }

  .record-item {
    .record-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;

      .handler {
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 600;
        color: #303133;
      }
    }

    .record-result {
      font-size: 13px;
      color: #606266;
      line-height: 1.6;
      padding: 8px 12px;
      background: #f5f7fa;
      border-radius: 4px;
    }
  }
}

.handle-form {
  margin-top: 10px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

// 响应式
@media (max-width: 768px) {
  .stat-row {
    flex-wrap: wrap;
  }

  .mini-stat {
    min-width: calc(50% - 10px);
  }

  .condition-box .condition-content {
    grid-template-columns: 1fr;
  }
}
</style>
