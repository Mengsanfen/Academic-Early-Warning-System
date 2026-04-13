<template>
  <div class="rules-container">
    <div class="page-header">
      <div>
        <h2>规则配置</h2>
        <p class="subtitle">按高校真实业务维护预警规则，可限定执行年级、班级，并按课程类型制定不同标准。</p>
      </div>
      <div class="header-actions">
        <el-button @click="handleExecute">
          <el-icon><VideoPlay /></el-icon>
          执行规则
        </el-button>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建规则
        </el-button>
      </div>
    </div>

    <el-card class="panel-card" shadow="never">
      <div class="toolbar">
        <div class="filters">
          <el-select v-model="filters.type" clearable placeholder="规则类型" @change="handleSearch">
            <el-option label="成绩预警" value="score" />
            <el-option label="考勤预警" value="attendance" />
            <el-option label="毕业风险" value="graduation" />
          </el-select>
          <el-select v-model="filters.is_active" clearable placeholder="启用状态" @change="handleSearch">
            <el-option label="已启用" :value="true" />
            <el-option label="已停用" :value="false" />
          </el-select>
        </div>
        <div class="toolbar-actions">
          <el-button @click="handleReset">重置</el-button>
          <el-button type="primary" @click="handleSearch">查询</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" stripe border>
        <el-table-column prop="name" label="规则名称" min-width="180">
          <template #default="{ row }">
            <div class="name-cell">
              <span>{{ row.name }}</span>
              <el-tag v-if="!row.is_active" size="small" type="info">停用</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="规则编码" width="170" />
        <el-table-column prop="type" label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)">{{ getTypeName(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="level" label="预警级别" width="110">
          <template #default="{ row }">
            <el-tag :type="getLevelTagType(row.level)">{{ getLevelName(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="实施对象" min-width="180">
          <template #default="{ row }">
            <div class="scope-cell">
              <el-tag :type="getTargetTypeTagType(row.target_type)">{{ getTargetTypeName(row.target_type) }}</el-tag>
              <span class="scope-text">{{ formatTargetSummary(row) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="规则条件" min-width="280" show-overflow-tooltip>
          <template #default="{ row }">
            {{ formatConditionSummary(row) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="handleToggle(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
              <el-button link type="primary" @click="handleCopy(row)">复制</el-button>
              <el-button link type="primary" @click="showConditions(row)">详情</el-button>
              <el-popconfirm title="确定删除此规则吗？" @confirm="handleDelete(row)">
                <template #reference>
                  <el-button link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="900px" :close-on-click-modal="false" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="104px">
        <div class="section-title">基础信息</div>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="规则名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入规则名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规则编码" prop="code">
              <el-input v-model="form.code" :disabled="isEdit" placeholder="例如 REQUIRED_CREDIT_SHORTAGE" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="规则类型" prop="type">
              <el-select v-model="form.type" style="width: 100%" @change="handleTypeChange">
                <el-option label="成绩预警" value="score" />
                <el-option label="考勤预警" value="attendance" />
                <el-option label="毕业风险" value="graduation" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="预警级别" prop="level">
              <el-select v-model="form.level" style="width: 100%">
                <el-option label="一般预警" value="warning" />
                <el-option label="严重预警" value="serious" />
                <el-option label="紧急预警" value="urgent" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <div class="section-title">实施对象</div>
        <el-form-item label="实施范围">
          <el-radio-group v-model="form.target_type" @change="handleTargetTypeChange">
            <el-radio-button v-for="item in templateOptions.target_types" :key="item.value" :label="item.value">
              {{ item.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.target_type === 'grades'" label="适用年级">
          <el-select v-model="form.target_grades" multiple filterable placeholder="请选择适用年级" style="width: 100%">
            <el-option v-for="item in gradeOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.target_type === 'classes'" label="适用班级">
          <el-select v-model="form.target_classes" multiple filterable placeholder="请选择适用班级" style="width: 100%">
            <el-option v-for="item in classOptions" :key="item.id" :label="formatClassOption(item)" :value="item.id" />
          </el-select>
        </el-form-item>

        <div class="section-title">规则条件</div>
        <el-form-item label="判定模式">
          <el-radio-group v-model="form.condition_mode">
            <el-radio-button label="standard">单项规则</el-radio-button>
            <el-radio-button label="composite">组合条件</el-radio-button>
            <el-radio-button label="comprehensive" :disabled="form.type !== 'graduation'">综合风险</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="form.condition_mode === 'standard'">
          <el-row :gutter="16" class="condition-row">
            <el-col :xs="24" :sm="12" :md="11">
              <el-form-item label="监测指标">
                <el-select v-model="form.standard.metric" style="width: 100%" @change="handleMetricChange">
                  <el-option v-for="item in filteredMetrics" :key="item.value" :label="item.label" :value="item.value ?? ''" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12" :md="5">
              <el-form-item label="运算符" label-width="72px">
                <el-select v-model="form.standard.operator" style="width: 100%">
                  <el-option v-for="item in templateOptions.operators" :key="item.value" :label="item.label" :value="item.value ?? ''" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8">
              <el-form-item label="阈值" label-width="56px">
                <el-input-number
                  v-model="form.standard.threshold"
                  :precision="2"
                  controls-position="right"
                  class="rule-number-input"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="统计窗口">
                <el-select v-model="form.standard.time_window" clearable :disabled="!selectedMetricMeta?.supports_time_window" style="width: 100%">
                  <el-option v-for="item in templateOptions.time_windows" :key="String(item.value)" :label="item.label" :value="item.value ?? ''" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="课程类型">
                <el-select v-model="form.standard.course_type" clearable :disabled="!selectedMetricMeta?.supports_course_type" style="width: 100%" placeholder="不限课程类型">
                  <el-option v-for="item in templateOptions.course_types" :key="item.value" :label="item.label" :value="item.value ?? ''" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-alert type="info" :closable="false" show-icon :title="selectedMetricTip" />
        </template>

        <template v-else-if="form.condition_mode === 'composite'">
          <div class="composite-toolbar">
            <div>
              <div class="composite-title">组合条件规则</div>
              <div class="composite-hint">适合毕业审核、分类学分、成绩与考勤联动等多指标场景。</div>
            </div>
            <el-radio-group v-model="form.composite.logic">
              <el-radio-button label="any">任一条件触发</el-radio-button>
              <el-radio-button label="all">全部条件同时触发</el-radio-button>
            </el-radio-group>
          </div>

          <div class="condition-list">
            <div v-for="(item, index) in form.composite.items" :key="index" class="condition-card">
              <div class="condition-card-header">
                <div>
                  <span class="condition-index">条件 {{ index + 1 }}</span>
                  <span class="condition-preview">{{ formatConditionItemPreview(item) }}</span>
                </div>
                <el-button
                  link
                  type="danger"
                  :disabled="form.composite.items.length === 1"
                  @click="removeCompositeCondition(index)"
                >
                  删除
                </el-button>
              </div>

              <el-row :gutter="14">
                <el-col :xs="24" :sm="12" :md="8">
                  <el-form-item label="条件名称" label-width="76px">
                    <el-input v-model="item.label" placeholder="如：必修学分要求" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12" :md="8">
                  <el-form-item label="监测指标" label-width="76px">
                    <el-select v-model="item.metric" style="width: 100%" @change="handleCompositeMetricChange(item)">
                      <el-option v-for="metric in filteredMetrics" :key="metric.value" :label="metric.label" :value="metric.value ?? ''" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12" :md="8">
                  <el-form-item label="课程类型" label-width="76px">
                    <el-select
                      v-model="item.course_type"
                      clearable
                      :disabled="!getCompositeMetricMeta(item)?.supports_course_type"
                      style="width: 100%"
                      placeholder="不限课程类型"
                    >
                      <el-option v-for="courseType in templateOptions.course_types" :key="courseType.value" :label="courseType.label" :value="courseType.value ?? ''" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="14">
                <el-col :xs="24" :sm="8">
                  <el-form-item label="运算符" label-width="76px">
                    <el-select v-model="item.operator" style="width: 100%">
                      <el-option v-for="operator in templateOptions.operators" :key="operator.value" :label="operator.label" :value="operator.value ?? ''" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="8">
                  <el-form-item label="阈值" label-width="56px">
                    <el-input-number v-model="item.threshold" :precision="2" controls-position="right" class="rule-number-input" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="8">
                  <el-form-item label="统计窗口" label-width="76px">
                    <el-select
                      v-model="item.time_window"
                      clearable
                      :disabled="!getCompositeMetricMeta(item)?.supports_time_window"
                      style="width: 100%"
                    >
                      <el-option v-for="window in templateOptions.time_windows" :key="String(window.value)" :label="window.label" :value="window.value ?? ''" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
            </div>
          </div>

          <el-button class="add-condition-btn" type="primary" plain @click="addCompositeCondition">
            <el-icon><Plus /></el-icon>
            添加条件
          </el-button>
        </template>

        <template v-else>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="挂科门数阈值">
                <el-input-number
                  v-model="form.comprehensive.fail_count_threshold"
                  :min="0"
                  :max="20"
                  controls-position="right"
                  class="rule-number-input"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="缺勤次数阈值">
                <el-input-number
                  v-model="form.comprehensive.absence_count_threshold"
                  :min="0"
                  :max="100"
                  controls-position="right"
                  class="rule-number-input"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-alert type="warning" :closable="false" show-icon title="综合风险会同时校验挂科门数与缺勤次数。" />
        </template>

        <div class="section-title">补充说明</div>
        <el-form-item label="规则描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入规则业务含义" />
        </el-form-item>
        <el-form-item label="预警文案">
          <el-input v-model="form.message_template" type="textarea" :rows="2" placeholder="支持 {student_name}、{metric_value}、{threshold}、{condition_summary} 等变量" />
        </el-form-item>
        <el-form-item label="立即启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存规则</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="conditionsDialogVisible" title="规则详情" width="620px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="规则名称">{{ currentRule?.name }}</el-descriptions-item>
        <el-descriptions-item label="实施对象">{{ currentRule ? formatTargetSummary(currentRule) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="规则说明">{{ currentRule ? formatConditionSummary(currentRule) : '-' }}</el-descriptions-item>
      </el-descriptions>
      <div class="conditions-json">
        <h4>原始条件</h4>
        <pre>{{ JSON.stringify(currentRule?.conditions, null, 2) }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, VideoPlay } from '@element-plus/icons-vue'
import {
  createRule,
  deleteRule,
  executeRules,
  getRules,
  getRuleTemplates,
  getTargetOptions,
  toggleRule,
  updateRule,
  type RuleCourseTypeOption,
  type RuleMetricOption,
  type RuleOperatorOption,
  type RuleTargetTypeOption,
  type RuleTimeWindowOption
} from '@/api/rule'
import type { AlertLevel, Rule, RuleType, TargetType } from '@/types'

interface TargetClassOption {
  id: number
  name: string
  grade: string
  department_name?: string
}

interface TemplateOptionsState {
  metrics: RuleMetricOption[]
  operators: RuleOperatorOption[]
  time_windows: RuleTimeWindowOption[]
  target_types: RuleTargetTypeOption[]
  course_types: RuleCourseTypeOption[]
}

type ConditionMode = 'standard' | 'composite' | 'comprehensive'
type CompositeLogic = 'any' | 'all'

interface RuleConditionItem {
  label: string
  metric: string
  operator: string
  threshold: number
  time_window: string
  course_type: string
}

const METRIC_TYPE_MAP: Record<RuleType, string[]> = {
  score: ['score', 'avg_score', 'fail_count', 'gpa', 'earned_credit', 'failed_credit'],
  attendance: ['attendance_rate', 'absence_count', 'late_count'],
  graduation: ['fail_count', 'gpa', 'earned_credit', 'failed_credit', 'attendance_rate', 'absence_count', 'late_count']
}

const DEFAULT_STANDARD_BY_TYPE: Record<RuleType, { metric: string; operator: string; threshold: number; time_window: string }> = {
  score: { metric: 'score', operator: '<', threshold: 60, time_window: '1term' },
  attendance: { metric: 'absence_count', operator: '>=', threshold: 3, time_window: '1term' },
  graduation: { metric: 'earned_credit', operator: '<', threshold: 30, time_window: '1y' }
}

const createConditionItem = (type: RuleType = 'graduation', overrides: Partial<RuleConditionItem> = {}): RuleConditionItem => {
  const preset = DEFAULT_STANDARD_BY_TYPE[type]
  return {
    label: '',
    metric: preset.metric,
    operator: preset.operator,
    threshold: preset.threshold,
    time_window: preset.time_window,
    course_type: '',
    ...overrides
  }
}

const filters = reactive({
  type: '' as RuleType | '',
  is_active: undefined as boolean | undefined
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const conditionsDialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const tableData = ref<Rule[]>([])
const currentRule = ref<Rule | null>(null)
const gradeOptions = ref<string[]>([])
const classOptions = ref<TargetClassOption[]>([])
const templateOptions = reactive<TemplateOptionsState>({
  metrics: [],
  operators: [],
  time_windows: [],
  target_types: [],
  course_types: []
})

const form = reactive({
  name: '',
  code: '',
  type: 'score' as RuleType,
  level: 'warning' as AlertLevel,
  description: '',
  message_template: '',
  is_active: true,
  target_type: 'all' as TargetType,
  target_grades: [] as string[],
  target_classes: [] as number[],
  condition_mode: 'standard' as ConditionMode,
  standard: {
    metric: 'score',
    operator: '<',
    threshold: 60,
    time_window: '1term',
    course_type: ''
  },
  composite: {
    logic: 'any' as CompositeLogic,
    items: [
      createConditionItem('graduation', { label: '必修学分要求', metric: 'earned_credit', operator: '<', threshold: 30, course_type: 'required', time_window: '1y' }),
      createConditionItem('graduation', { label: '选修学分要求', metric: 'earned_credit', operator: '<', threshold: 8, course_type: 'elective', time_window: '1y' })
    ] as RuleConditionItem[]
  },
  comprehensive: {
    fail_count_threshold: 2,
    absence_count_threshold: 3
  }
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入规则编码', trigger: 'blur' },
    { pattern: /^[A-Z0-9_]+$/, message: '规则编码仅支持大写字母、数字和下划线', trigger: 'blur' }
  ],
  type: [{ required: true, message: '请选择规则类型', trigger: 'change' }]
}

const dialogTitle = computed(() => (isEdit.value ? '编辑规则' : '新建规则'))
const filteredMetrics = computed(() => templateOptions.metrics.filter(item => (METRIC_TYPE_MAP[form.type] || []).includes(item.value)))
const selectedMetricMeta = computed(() => filteredMetrics.value.find(item => item.value === form.standard.metric) || filteredMetrics.value[0])
const selectedMetricTip = computed(() => {
  if (!selectedMetricMeta.value) return '请选择监测指标。'
  return `${selectedMetricMeta.value.description}${selectedMetricMeta.value.supports_course_type ? ' 当前指标支持按课程类型细分。' : ''}`
})

const getTypeName = (type: RuleType) => ({ score: '成绩预警', attendance: '考勤预警', graduation: '毕业风险' }[type] || type)
const getTypeTagType = (type: RuleType): 'success' | 'warning' | 'info' | 'danger' | undefined => {
  const map: Record<RuleType, 'success' | 'warning' | 'info' | 'danger' | undefined> = { score: 'info', attendance: 'success', graduation: 'warning' }
  return map[type]
}
const getLevelName = (level: AlertLevel) => ({ warning: '一般预警', serious: '严重预警', urgent: '紧急预警' }[level] || level)
const getLevelTagType = (level: AlertLevel): 'success' | 'warning' | 'info' | 'danger' | undefined => {
  const map: Record<AlertLevel, 'success' | 'warning' | 'info' | 'danger' | undefined> = { warning: 'warning', serious: 'danger', urgent: undefined }
  return map[level]
}
const getTargetTypeName = (type?: TargetType) => ({ all: '全体学生', grades: '按年级', classes: '按班级' }[type || 'all'] || type || '全体学生')
const getTargetTypeTagType = (type?: TargetType): 'success' | 'warning' | 'info' | 'danger' | undefined => {
  const map: Record<TargetType, 'success' | 'warning' | 'info' | 'danger' | undefined> = { all: 'info', grades: 'success', classes: 'warning' }
  return map[type || 'all']
}
const getMetricLabel = (metric?: string) => templateOptions.metrics.find(item => item.value === metric)?.label || metric || '未配置'
const getCourseTypeLabel = (courseType?: string | null) => templateOptions.course_types.find(item => item.value === courseType)?.label || courseType || '不限课程类型'
const formatClassOption = (item: TargetClassOption) => (item.department_name ? `${item.grade} ${item.name} · ${item.department_name}` : `${item.grade} ${item.name}`)

const formatTargetSummary = (row: Rule) => {
  if (row.target_type === 'grades') {
    const grades = row.target_grades || []
    return grades.length ? `按年级：${grades.join('、')}` : '按年级：未配置'
  }
  if (row.target_type === 'classes') {
    const ids = row.target_classes || []
    const names = ids
      .map(id => classOptions.value.find(item => item.id === id))
      .filter((item): item is TargetClassOption => Boolean(item))
      .map(item => item.name)
    return ids.length ? `按班级：${names.length ? names.join('、') : `共 ${ids.length} 个班级`}` : '按班级：未配置'
  }
  return '适用于全体学生'
}

const formatConditionSummary = (row: Rule) => {
  const conditions = row.conditions || {}
  if (conditions.mode === 'comprehensive') {
    return `综合风险：挂科门数 >= ${conditions.fail_count_threshold} 且缺勤次数 >= ${conditions.absence_count_threshold}`
  }
  if (conditions.mode === 'composite') {
    const logicLabel = conditions.logic === 'all' ? '全部满足' : '任一触发'
    const itemSummary = Array.isArray(conditions.items)
      ? conditions.items
          .map((item: any) => {
            const operatorLabel = templateOptions.operators.find(option => option.value === item.operator)?.label || item.operator || ''
            const courseLabel = item.course_type ? `·${getCourseTypeLabel(item.course_type)}` : ''
            return `${item.label || getMetricLabel(item.metric)}${courseLabel} ${operatorLabel} ${item.threshold ?? '-'}`
          })
          .join('；')
      : '未配置条件'
    return `组合规则（${logicLabel}）：${itemSummary}`
  }
  const operatorLabel = templateOptions.operators.find(item => item.value === conditions.operator)?.label || conditions.operator || ''
  const extras: string[] = []
  if (conditions.time_window) {
    extras.push(templateOptions.time_windows.find(item => item.value === conditions.time_window)?.label || conditions.time_window)
  }
  if (conditions.course_type) {
    extras.push(getCourseTypeLabel(conditions.course_type))
  }
  return `${getMetricLabel(conditions.metric)} ${operatorLabel} ${conditions.threshold ?? '-'}${extras.length ? `（${extras.join('，')}）` : ''}`
}

const resetStandardByType = (type: RuleType) => {
  const preset = DEFAULT_STANDARD_BY_TYPE[type]
  form.standard.metric = preset.metric
  form.standard.operator = preset.operator
  form.standard.threshold = preset.threshold
  form.standard.time_window = preset.time_window
  form.standard.course_type = ''
}

const handleTypeChange = () => {
  if (form.type !== 'graduation' && form.condition_mode === 'comprehensive') {
    form.condition_mode = 'standard'
  }
  const metricList = filteredMetrics.value.map(item => item.value)
  if (!metricList.includes(form.standard.metric)) {
    resetStandardByType(form.type)
  }
  form.composite.items.forEach(item => {
    if (!metricList.includes(item.metric)) {
      Object.assign(item, createConditionItem(form.type, { label: item.label }))
    }
    handleCompositeMetricChange(item)
  })
}

const handleMetricChange = () => {
  if (!selectedMetricMeta.value?.supports_course_type) {
    form.standard.course_type = ''
  }
  if (!selectedMetricMeta.value?.supports_time_window) {
    form.standard.time_window = ''
  }
}

const getCompositeMetricMeta = (item: RuleConditionItem) => {
  return filteredMetrics.value.find(metric => metric.value === item.metric) || filteredMetrics.value[0]
}

const handleCompositeMetricChange = (item: RuleConditionItem) => {
  const meta = getCompositeMetricMeta(item)
  if (!meta?.supports_course_type) {
    item.course_type = ''
  }
  if (!meta?.supports_time_window) {
    item.time_window = ''
  }
}

const addCompositeCondition = () => {
  form.composite.items.push(createConditionItem(form.type))
}

const removeCompositeCondition = (index: number) => {
  if (form.composite.items.length <= 1) return
  form.composite.items.splice(index, 1)
}

const formatConditionItemPreview = (item: RuleConditionItem) => {
  const metricLabel = getMetricLabel(item.metric)
  const operatorLabel = templateOptions.operators.find(option => option.value === item.operator)?.label || item.operator
  const courseLabel = item.course_type ? ` · ${getCourseTypeLabel(item.course_type)}` : ''
  return `${item.label || metricLabel}${courseLabel} ${operatorLabel} ${item.threshold}`
}

const handleTargetTypeChange = () => {
  form.target_grades = []
  form.target_classes = []
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getRules({
      page: pagination.page,
      page_size: pagination.pageSize,
      type: filters.type || undefined,
      is_active: filters.is_active
    })
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('获取规则列表失败', error)
    ElMessage.error('获取规则列表失败')
  } finally {
    loading.value = false
  }
}

const fetchMetadata = async () => {
  try {
    const [templateRes, targetRes] = await Promise.all([getRuleTemplates(), getTargetOptions()])
    templateOptions.metrics = templateRes.metrics || []
    templateOptions.operators = templateRes.operators || []
    templateOptions.time_windows = templateRes.time_windows || []
    templateOptions.target_types = templateRes.target_types || []
    templateOptions.course_types = templateRes.course_types || []
    gradeOptions.value = targetRes.grades || []
    classOptions.value = targetRes.classes || []
  } catch (error) {
    console.error('获取规则配置元数据失败', error)
    ElMessage.error('获取规则配置选项失败')
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  filters.type = ''
  filters.is_active = undefined
  handleSearch()
}

const buildConditionsPayload = () => {
  if (form.condition_mode === 'comprehensive') {
    return {
      mode: 'comprehensive',
      fail_count_threshold: Number(form.comprehensive.fail_count_threshold),
      absence_count_threshold: Number(form.comprehensive.absence_count_threshold)
    }
  }
  if (form.condition_mode === 'composite') {
    return {
      mode: 'composite',
      logic: form.composite.logic,
      items: form.composite.items.map(item => ({
        label: item.label || undefined,
        metric: item.metric,
        operator: item.operator,
        threshold: Number(item.threshold),
        time_window: item.time_window || null,
        course_type: item.course_type || null
      }))
    }
  }
  return {
    metric: form.standard.metric,
    operator: form.standard.operator,
    threshold: Number(form.standard.threshold),
    time_window: form.standard.time_window || null,
    course_type: form.standard.course_type || null
  }
}

const validateBusinessForm = () => {
  if (form.target_type === 'grades' && form.target_grades.length === 0) {
    ElMessage.warning('请至少选择一个适用年级')
    return false
  }
  if (form.target_type === 'classes' && form.target_classes.length === 0) {
    ElMessage.warning('请至少选择一个适用班级')
    return false
  }
  if (form.condition_mode === 'standard') {
    if (!form.standard.metric || !form.standard.operator || form.standard.threshold === null || form.standard.threshold === undefined) {
      ElMessage.warning('请完整填写规则条件')
      return false
    }
  }
  if (form.condition_mode === 'composite') {
    if (!form.composite.items.length) {
      ElMessage.warning('组合规则至少需要一个条件')
      return false
    }
    const invalidIndex = form.composite.items.findIndex(item => !item.metric || !item.operator || item.threshold === null || item.threshold === undefined)
    if (invalidIndex >= 0) {
      ElMessage.warning(`请完整填写组合条件 ${invalidIndex + 1}`)
      return false
    }
  }
  return true
}

const resetFormData = () => {
  Object.assign(form, {
    name: '',
    code: '',
    type: 'score',
    level: 'warning',
    description: '',
    message_template: '',
    is_active: true,
    target_type: 'all',
    target_grades: [],
    target_classes: [],
    condition_mode: 'standard',
    standard: {
      metric: 'score',
      operator: '<',
      threshold: 60,
      time_window: '1term',
      course_type: ''
    },
    composite: {
      logic: 'any' as CompositeLogic,
      items: [
        createConditionItem('graduation', { label: '必修学分要求', metric: 'earned_credit', operator: '<', threshold: 30, course_type: 'required', time_window: '1y' }),
        createConditionItem('graduation', { label: '选修学分要求', metric: 'earned_credit', operator: '<', threshold: 8, course_type: 'elective', time_window: '1y' })
      ]
    },
    comprehensive: {
      fail_count_threshold: 2,
      absence_count_threshold: 3
    }
  })
}

const hydrateForm = (row: Rule) => {
  form.name = row.name
  form.code = row.code
  form.type = row.type
  form.level = row.level
  form.description = row.description || ''
  form.message_template = row.message_template || ''
  form.is_active = row.is_active
  form.target_type = row.target_type || 'all'
  form.target_grades = [...(row.target_grades || [])]
  form.target_classes = [...(row.target_classes || [])]
  if (row.conditions?.mode === 'comprehensive') {
    form.condition_mode = 'comprehensive'
    form.comprehensive.fail_count_threshold = Number(row.conditions.fail_count_threshold ?? 2)
    form.comprehensive.absence_count_threshold = Number(row.conditions.absence_count_threshold ?? 3)
    resetStandardByType(row.type)
  } else if (row.conditions?.mode === 'composite') {
    form.condition_mode = 'composite'
    form.composite.logic = row.conditions.logic === 'all' ? 'all' : 'any'
    form.composite.items = Array.isArray(row.conditions.items) && row.conditions.items.length
      ? row.conditions.items.map((item: any) => createConditionItem(row.type, {
          label: item.label || '',
          metric: item.metric || DEFAULT_STANDARD_BY_TYPE[row.type].metric,
          operator: item.operator || DEFAULT_STANDARD_BY_TYPE[row.type].operator,
          threshold: Number(item.threshold ?? DEFAULT_STANDARD_BY_TYPE[row.type].threshold),
          time_window: item.time_window || '',
          course_type: item.course_type || ''
        }))
      : [createConditionItem(row.type)]
    resetStandardByType(row.type)
  } else {
    form.condition_mode = 'standard'
    form.standard.metric = row.conditions?.metric || DEFAULT_STANDARD_BY_TYPE[row.type].metric
    form.standard.operator = row.conditions?.operator || DEFAULT_STANDARD_BY_TYPE[row.type].operator
    form.standard.threshold = Number(row.conditions?.threshold ?? DEFAULT_STANDARD_BY_TYPE[row.type].threshold)
    form.standard.time_window = row.conditions?.time_window ?? DEFAULT_STANDARD_BY_TYPE[row.type].time_window
    form.standard.course_type = row.conditions?.course_type || ''
  }
}

const handleCreate = () => {
  isEdit.value = false
  editId.value = null
  resetFormData()
  dialogVisible.value = true
}

const handleEdit = (row: Rule) => {
  isEdit.value = true
  editId.value = row.id
  hydrateForm(row)
  dialogVisible.value = true
}

const handleCopy = (row: Rule) => {
  isEdit.value = false
  editId.value = null
  hydrateForm(row)
  const suffix = Date.now().toString().slice(-4)
  form.name = `${row.name}（副本）`
  form.code = `${row.code}_COPY_${suffix}`
  form.is_active = false
  dialogVisible.value = true
}

const handleDelete = async (row: Rule) => {
  try {
    await deleteRule(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error) {
    console.error('删除规则失败', error)
    ElMessage.error('删除规则失败')
  }
}

const handleToggle = async (row: Rule) => {
  try {
    await toggleRule(row.id)
    ElMessage.success(row.is_active ? '规则已启用' : '规则已停用')
  } catch (error) {
    row.is_active = !row.is_active
    console.error('切换规则状态失败', error)
    ElMessage.error('切换规则状态失败')
  }
}

const handleExecute = async () => {
  try {
    await ElMessageBox.confirm('确定立即执行所有已启用规则吗？执行会基于当前实施对象和课程类型重新计算。', '执行规则', { type: 'warning' })
    const res = await executeRules()
    ElMessage.success(res.message || '规则执行完成')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('执行规则失败', error)
      ElMessage.error('执行规则失败')
    }
  }
}

const showConditions = (row: Rule) => {
  currentRule.value = row
  conditionsDialogVisible.value = true
}

const resetForm = () => {
  formRef.value?.resetFields()
  resetFormData()
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid || !validateBusinessForm()) return

  submitting.value = true
  try {
    const payload = {
      name: form.name,
      code: form.code,
      type: form.type,
      level: form.level,
      description: form.description || undefined,
      message_template: form.message_template || undefined,
      is_active: form.is_active,
      target_type: form.target_type,
      target_grades: form.target_type === 'grades' ? form.target_grades : [],
      target_classes: form.target_type === 'classes' ? form.target_classes : [],
      conditions: buildConditionsPayload()
    }

    if (isEdit.value && editId.value) {
      await updateRule(editId.value, payload)
      ElMessage.success('规则更新成功')
    } else {
      await createRule(payload)
      ElMessage.success('规则创建成功')
    }

    dialogVisible.value = false
    fetchData()
  } catch (error: any) {
    console.error('保存规则失败', error)
    ElMessage.error(error?.response?.data?.detail || '保存规则失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await fetchMetadata()
  handleTypeChange()
  fetchData()
})
</script>

<style scoped lang="scss">
.rules-container { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 20px; }
.page-header h2 { margin: 0 0 8px; font-size: 32px; font-weight: 700; color: #1f2937; }
.subtitle { margin: 0; color: #64748b; line-height: 1.6; }
.header-actions, .toolbar-actions, .row-actions, .name-cell, .scope-cell { display: flex; align-items: center; gap: 8px; }
.panel-card { border-radius: 18px; }
.toolbar { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.filters { display: grid; grid-template-columns: repeat(2, minmax(180px, 240px)); gap: 12px; }
.scope-text { color: #64748b; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
.section-title { margin: 8px 0 14px; font-size: 15px; font-weight: 700; color: #1f2937; }
.condition-row :deep(.el-form-item) { margin-bottom: 18px; }
.rule-number-input { width: 100%; min-width: 168px; }
.rule-number-input :deep(.el-input__wrapper) { justify-content: flex-start; }
.rule-number-input :deep(.el-input__inner) { text-align: left; }
.composite-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  margin-bottom: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef6ff 100%);
}
.composite-title { font-weight: 700; color: #0f172a; }
.composite-hint { margin-top: 4px; color: #64748b; font-size: 13px; }
.condition-list { display: flex; flex-direction: column; gap: 14px; }
.condition-card {
  padding: 16px;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
}
.condition-card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 14px; }
.condition-index { font-weight: 700; color: #2563eb; }
.condition-preview { margin-left: 10px; color: #64748b; font-size: 13px; }
.add-condition-btn { width: 100%; margin-top: 12px; border-style: dashed; }
.conditions-json { margin-top: 16px; }
.conditions-json h4 { margin-bottom: 8px; color: #1f2937; }
.conditions-json pre { margin: 0; padding: 16px; border-radius: 14px; background: #0f172a; color: #e2e8f0; overflow: auto; font-size: 12px; line-height: 1.6; }
@media (max-width: 960px) {
  .page-header { flex-direction: column; }
  .header-actions, .toolbar-actions { width: 100%; }
  .header-actions :deep(.el-button), .toolbar-actions :deep(.el-button) { flex: 1; }
  .filters { grid-template-columns: 1fr; }
  .rule-number-input { min-width: 100%; }
  .composite-toolbar { align-items: stretch; flex-direction: column; }
  .condition-card-header { align-items: flex-start; flex-direction: column; }
}
</style>


