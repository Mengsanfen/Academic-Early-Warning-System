<template>
  <el-dialog
    v-model="visible"
    title="批量导入学生"
    width="600px"
    :close-on-click-modal="false"
    @closed="handleClose"
  >
    <div class="import-content">
      <!-- 步骤1：上传文件 -->
      <div v-show="currentStep === 0" class="upload-section">
        <div class="template-download">
          <span>请先下载导入模板，按照模板格式填写学生数据</span>
          <el-button type="primary" link @click="handleDownloadTemplate">
            <el-icon><Download /></el-icon>
            下载模板
          </el-button>
        </div>

        <el-upload
          ref="uploadRef"
          class="upload-area"
          drag
          :auto-upload="false"
          :limit="1"
          accept=".xlsx,.xls"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将 Excel 文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              只能上传 xlsx/xls 文件，且不超过 5MB
            </div>
          </template>
        </el-upload>

        <div class="import-options">
          <el-form label-width="120px">
            <el-form-item label="同时创建账号">
              <el-switch v-model="createAccounts" />
              <span class="option-hint">开启后将自动为学生创建登录账号</span>
            </el-form-item>
            <el-form-item v-if="createAccounts" label="默认密码">
              <el-radio-group v-model="defaultPasswordType">
                <el-radio label="student_no">学号</el-radio>
                <el-radio label="phone">手机号后6位</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- 步骤2：导入结果 -->
      <div v-show="currentStep === 1" class="result-section">
        <div v-if="importing" class="importing">
          <el-icon class="is-loading" :size="40"><Loading /></el-icon>
          <p>正在导入数据，请稍候...</p>
        </div>

        <div v-else class="import-result">
          <el-result
            :icon="importResult.failed === 0 ? 'success' : 'warning'"
            :title="importResult.failed === 0 ? '导入成功' : '导入完成（部分失败）'"
          >
            <template #sub-title>
              <div class="result-stats">
                <p>总计: <strong>{{ importResult.total }}</strong> 条</p>
                <p>成功: <strong class="success">{{ importResult.success }}</strong> 条</p>
                <p>失败: <strong class="error">{{ importResult.failed }}</strong> 条</p>
                <p v-if="importResult.created_users > 0">
                  创建账号: <strong class="info">{{ importResult.created_users }}</strong> 个
                </p>
              </div>
            </template>
            <template #extra>
              <div v-if="importResult.errors.length > 0" class="error-list">
                <el-collapse>
                  <el-collapse-item title="查看错误详情" name="errors">
                    <div class="errors">
                      <p v-for="(error, index) in importResult.errors" :key="index" class="error-item">
                        {{ error }}
                      </p>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </template>
          </el-result>
        </div>
      </div>
    </div>

    <template #footer>
      <template v-if="currentStep === 0">
        <el-button @click="visible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!selectedFile"
          :loading="importing"
          @click="handleImport"
        >
          开始导入
        </el-button>
      </template>
      <template v-else>
        <el-button type="primary" @click="handleClose">
          完成
        </el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, UploadFilled, Loading } from '@element-plus/icons-vue'
import { downloadTemplate, importStudents } from '@/api/import'
import type { ImportResult } from '@/types'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const visible = ref(props.modelValue)
const currentStep = ref(0)
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const importing = ref(false)
const createAccounts = ref(true)
const defaultPasswordType = ref('student_no')

const importResult = ref<ImportResult>({
  total: 0,
  success: 0,
  failed: 0,
  errors: [],
  created_users: 0
})

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

// 下载模板
const handleDownloadTemplate = async () => {
  try {
    const blob = await downloadTemplate()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'student_import_template.xlsx'
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('模板下载成功')
  } catch (error) {
    ElMessage.error('模板下载失败')
  }
}

// 文件选择
const handleFileChange = (file: any) => {
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过5MB')
    return false
  }
  selectedFile.value = file.raw
}

// 文件移除
const handleFileRemove = () => {
  selectedFile.value = null
}

// 开始导入
const handleImport = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  currentStep.value = 1
  importing.value = true

  try {
    const result = await importStudents(
      selectedFile.value,
      createAccounts.value,
      defaultPasswordType.value
    )
    importResult.value = result

    if (result.success > 0) {
      emit('success')
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '导入失败')
    importResult.value = {
      total: 0,
      success: 0,
      failed: 0,
      errors: [error?.response?.data?.detail || '导入失败'],
      created_users: 0
    }
  } finally {
    importing.value = false
  }
}

// 关闭对话框
const handleClose = () => {
  visible.value = false
  currentStep.value = 0
  selectedFile.value = null
  importResult.value = {
    total: 0,
    success: 0,
    failed: 0,
    errors: [],
    created_users: 0
  }
}
</script>

<style scoped lang="scss">
.import-content {
  .template-download {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: #f5f7fa;
    border-radius: 8px;
    margin-bottom: 20px;

    span {
      color: #606266;
      font-size: 14px;
    }
  }

  .upload-area {
    margin-bottom: 20px;
  }

  .import-options {
    padding: 16px;
    background: #fafafa;
    border-radius: 8px;

    .option-hint {
      margin-left: 12px;
      font-size: 12px;
      color: #909399;
    }
  }

  .importing {
    text-align: center;
    padding: 40px 0;

    p {
      margin-top: 16px;
      color: #909399;
    }
  }

  .result-section {
    .result-stats {
      p {
        margin: 8px 0;
        font-size: 14px;

        strong {
          font-size: 16px;

          &.success {
            color: #67c23a;
          }

          &.error {
            color: #f56c6c;
          }

          &.info {
            color: #409eff;
          }
        }
      }
    }

    .error-list {
      margin-top: 16px;
      text-align: left;

      .errors {
        max-height: 200px;
        overflow-y: auto;

        .error-item {
          margin: 4px 0;
          font-size: 13px;
          color: #f56c6c;
        }
      }
    }
  }
}
</style>
