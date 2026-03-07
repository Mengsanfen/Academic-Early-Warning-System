<template>
  <div class="rules-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>规则配置</h2>
      <p class="subtitle">配置学业预警规则，系统将根据规则自动检测学生数据并生成预警</p>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="filters">
        <el-select v-model="filters.type" placeholder="规则类型" clearable style="width: 160px" @change="handleSearch">
          <el-option label="成绩预警" value="score" />
          <el-option label="考勤预警" value="attendance" />
          <el-option label="毕业风险预警" value="graduation" />
        </el-select>
        <el-select v-model="filters.is_active" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
          <el-option label="已启用" :value="true" />
          <el-option label="已禁用" :value="false" />
        </el-select>
      </div>
      <div class="actions">
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建规则
        </el-button>
        <el-button @click="handleExecute">
          <el-icon><VideoPlay /></el-icon>
          执行规则
        </el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="name" label="规则名称" min-width="150">
          <template #default="{ row }">
            <div class="rule-name">
              <span>{{ row.name }}</span>
              <el-tag v-if="!row.is_active" type="info" size="small">已禁用</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="规则编码" width="140" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)">
              {{ getTypeName(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="level" label="预警级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getLevelTagType(row.level)" effect="dark">
              {{ getLevelName(row.level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="规则描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="规则条件" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="showConditions(row)">
              查看条件
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="handleToggle(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="primary" @click="handleCopy(row)">复制</el-button>
            <el-popconfirm
              title="确定要删除此规则吗？"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="680px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="规则名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入规则名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规则编码" prop="code">
              <el-input v-model="form.code" placeholder="请输入唯一编码" :disabled="isEdit" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="规则类型" prop="type">
              <el-select v-model="form.type" placeholder="请选择规则类型" style="width: 100%">
                <el-option label="成绩预警" value="score" />
                <el-option label="考勤预警" value="attendance" />
                <el-option label="毕业风险预警" value="graduation" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="预警级别" prop="level">
              <el-select v-model="form.level" placeholder="请选择预警级别" style="width: 100%">
                <el-option label="一般预警" value="warning" />
                <el-option label="严重预警" value="serious" />
                <el-option label="紧急预警" value="urgent" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="规则描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="请输入规则描述"
          />
        </el-form-item>

        <el-form-item label="预警消息" prop="message_template">
          <el-input
            v-model="form.message_template"
            type="textarea"
            :rows="2"
            placeholder="请输入预警消息模板，可使用 {student_name}、{score} 等变量"
          />
        </el-form-item>

        <!-- 规则条件配置 -->
        <el-divider content-position="left">规则条件</el-divider>

        <!-- 成绩预警条件 -->
        <template v-if="form.type === 'score'">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="成绩阈值">
                <el-input-number
                  v-model="form.conditions.score_threshold"
                  :min="0"
                  :max="100"
                  placeholder="低于此分数触发"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="课程数量">
                <el-input-number
                  v-model="form.conditions.course_count"
                  :min="1"
                  :max="20"
                  placeholder="不及格课程数"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="统计学期">
                <el-select v-model="form.conditions.semester_type" style="width: 100%">
                  <el-option label="当前学期" value="current" />
                  <el-option label="最近两学期" value="last_two" />
                  <el-option label="全部学期" value="all" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="GPA阈值">
                <el-input-number
                  v-model="form.conditions.gpa_threshold"
                  :min="0"
                  :max="4"
                  :precision="2"
                  :step="0.1"
                  placeholder="GPA低于此值触发"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </template>

        <!-- 考勤预警条件 -->
        <template v-if="form.type === 'attendance'">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="缺勤阈值">
                <el-input-number
                  v-model="form.conditions.absence_threshold"
                  :min="1"
                  :max="50"
                  placeholder="缺勤次数"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="统计周期">
                <el-select v-model="form.conditions.period" style="width: 100%">
                  <el-option label="近一个月" value="month" />
                  <el-option label="近一学期" value="semester" />
                  <el-option label="全部" value="all" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="迟到阈值">
                <el-input-number
                  v-model="form.conditions.late_threshold"
                  :min="1"
                  :max="50"
                  placeholder="迟到次数"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="缺勤率">
                <el-input-number
                  v-model="form.conditions.absence_rate"
                  :min="0"
                  :max="100"
                  placeholder="缺勤率 %"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </template>

        <!-- 毕业风险预警条件 -->
        <template v-if="form.type === 'graduation'">
          <el-form-item label="触发条件">
            <el-checkbox-group v-model="form.conditions.triggers">
              <el-checkbox label="score">成绩不合格</el-checkbox>
              <el-checkbox label="attendance">考勤异常</el-checkbox>
              <el-checkbox label="gpa">GPA过低</el-checkbox>
              <el-checkbox label="credit">学分不足</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="组合方式">
            <el-radio-group v-model="form.conditions.combination">
              <el-radio label="any">满足任一条件</el-radio>
              <el-radio label="all">满足所有条件</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>

        <el-form-item label="立即启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看条件对话框 -->
    <el-dialog
      v-model="conditionsDialogVisible"
      title="规则条件详情"
      width="500px"
    >
      <div class="conditions-detail">
        <pre>{{ JSON.stringify(currentRule?.conditions, null, 2) }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, VideoPlay } from '@element-plus/icons-vue'
import { getRules, createRule, updateRule, deleteRule, toggleRule, executeRules } from '@/api/rule'
import type { Rule, RuleType, AlertLevel } from '@/types'

// 筛选条件
const filters = reactive({
  type: '',
  is_active: undefined as boolean | undefined
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 数据
const loading = ref(false)
const tableData = ref<Rule[]>([])

// 对话框
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const isEdit = ref(false)
const editId = ref<number | null>(null)

// 查看条件对话框
const conditionsDialogVisible = ref(false)
const currentRule = ref<Rule | null>(null)

// 表单数据
const form = reactive({
  name: '',
  code: '',
  type: 'score' as RuleType,
  level: 'warning' as AlertLevel,
  description: '',
  message_template: '',
  is_active: true,
  conditions: {
    // 成绩条件
    score_threshold: 60,
    course_count: 2,
    semester_type: 'current',
    gpa_threshold: 2.0,
    // 考勤条件
    absence_threshold: 3,
    late_threshold: 5,
    period: 'semester',
    absence_rate: 20,
    // 综合条件
    triggers: [] as string[],
    combination: 'any'
  }
})

// 表单验证规则
const rules: FormRules = {
  name: [
    { required: true, message: '请输入规则名称', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入规则编码', trigger: 'blur' },
    { pattern: /^[A-Z_]+$/, message: '编码只能包含大写字母和下划线', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择规则类型', trigger: 'change' }
  ],
  level: [
    { required: true, message: '请选择预警级别', trigger: 'change' }
  ]
}

// 计算属性
const dialogTitle = computed(() => isEdit.value ? '编辑规则' : '新建规则')

// 获取类型名称
const getTypeName = (type: RuleType) => {
  const map: Record<RuleType, string> = {
    score: '成绩',
    attendance: '考勤',
    graduation: '毕业风险'
  }
  return map[type] || type
}

// 获取类型标签类型
const getTypeTagType = (type: RuleType) => {
  const map: Record<RuleType, string> = {
    score: 'primary',
    attendance: 'success',
    graduation: 'warning'
  }
  return map[type] || ''
}

// 获取级别名称
const getLevelName = (level: AlertLevel) => {
  const map: Record<AlertLevel, string> = {
    warning: '一般',
    serious: '严重',
    urgent: '紧急'
  }
  return map[level] || level
}

// 获取级别标签类型
const getLevelTagType = (level: AlertLevel) => {
  const map: Record<AlertLevel, string> = {
    warning: 'warning',
    serious: 'danger',
    urgent: ''
  }
  return map[level] || ''
}

// 获取数据
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
    console.error('获取规则列表失败:', error)
    ElMessage.error('获取规则列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

// 创建规则
const handleCreate = () => {
  isEdit.value = false
  editId.value = null
  resetFormData()
  dialogVisible.value = true
}

// 编辑规则
const handleEdit = (row: Rule) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    name: row.name,
    code: row.code,
    type: row.type,
    level: row.level,
    description: row.description || '',
    message_template: row.message_template || '',
    is_active: row.is_active,
    conditions: { ...form.conditions, ...row.conditions }
  })
  dialogVisible.value = true
}

// 复制规则
const handleCopy = (row: Rule) => {
  isEdit.value = false
  editId.value = null
  Object.assign(form, {
    name: `${row.name} (副本)`,
    code: `${row.code}_COPY`,
    type: row.type,
    level: row.level,
    description: row.description || '',
    message_template: row.message_template || '',
    is_active: false,
    conditions: { ...form.conditions, ...row.conditions }
  })
  dialogVisible.value = true
}

// 删除规则
const handleDelete = async (row: Rule) => {
  try {
    await deleteRule(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error('删除失败')
  }
}

// 切换规则状态
const handleToggle = async (row: Rule) => {
  try {
    await toggleRule(row.id)
    ElMessage.success(row.is_active ? '规则已启用' : '规则已禁用')
  } catch (error) {
    console.error('切换状态失败:', error)
    row.is_active = !row.is_active
    ElMessage.error('操作失败')
  }
}

// 执行规则
const handleExecute = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要执行所有启用的规则吗？这可能需要一些时间。',
      '执行规则',
      { type: 'warning' }
    )
    const res = await executeRules()
    ElMessage.success(res.message || '规则执行完成')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('执行规则失败:', error)
      ElMessage.error('执行规则失败')
    }
  }
}

// 显示条件详情
const showConditions = (row: Rule) => {
  currentRule.value = row
  conditionsDialogVisible.value = true
}

// 重置表单数据
const resetFormData = () => {
  Object.assign(form, {
    name: '',
    code: '',
    type: 'score',
    level: 'warning',
    description: '',
    message_template: '',
    is_active: true,
    conditions: {
      score_threshold: 60,
      course_count: 2,
      semester_type: 'current',
      gpa_threshold: 2.0,
      absence_threshold: 3,
      late_threshold: 5,
      period: 'semester',
      absence_rate: 20,
      triggers: [],
      combination: 'any'
    }
  })
}

// 重置表单
const resetForm = () => {
  formRef.value?.resetFields()
  resetFormData()
}

// 提交表单
const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const data = {
      name: form.name,
      code: form.code,
      type: form.type,
      level: form.level,
      description: form.description,
      message_template: form.message_template,
      is_active: form.is_active,
      conditions: form.conditions
    }

    if (isEdit.value && editId.value) {
      await updateRule(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createRule(data)
      ElMessage.success('创建成功')
    }

    dialogVisible.value = false
    fetchData()
  } catch (error: any) {
    console.error('保存失败:', error)
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped lang="scss">
.rules-container {
  padding: 20px;

  .page-header {
    margin-bottom: 20px;

    h2 {
      margin: 0 0 8px 0;
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }

    .subtitle {
      margin: 0;
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .filters {
      display: flex;
      gap: 12px;
    }

    .actions {
      display: flex;
      gap: 12px;
    }
  }

  .table-card {
    .rule-name {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    padding: 16px 0 0;
  }

  .conditions-detail {
    background: var(--el-fill-color-light);
    border-radius: 8px;
    padding: 16px;

    pre {
      margin: 0;
      font-family: 'Fira Code', monospace;
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }
}
</style>
