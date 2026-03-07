import { request } from '@/utils/request'
import type { ImportResult } from '@/types'

// 下载导入模板
export function downloadTemplate() {
  return request.get('/import/template', {
    responseType: 'blob'
  })
}

// 批量导入学生
export function importStudents(file: File, createAccounts: boolean = true, defaultPasswordType: string = 'student_no') {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<ImportResult>(`/import/import?create_accounts=${createAccounts}&default_password_type=${defaultPasswordType}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 导出学生数据
export function exportStudents(classId?: number) {
  const url = classId ? `/import/export?class_id=${classId}` : '/import/export'
  return request.get(url, {
    responseType: 'blob'
  })
}

// ==================== 成绩导入 ====================

// 下载成绩导入模板
export function downloadScoreTemplate() {
  return request.get('/import/scores/template', {
    responseType: 'blob'
  })
}

// 批量导入成绩
export function importScores(file: File, updateExisting: boolean = false) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<ImportResult>(`/import/scores/import?update_existing=${updateExisting}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// ==================== 考勤导入 ====================

// 下载考勤导入模板
export function downloadAttendanceTemplate() {
  return request.get('/import/attendances/template', {
    responseType: 'blob'
  })
}

// 批量导入考勤
export function importAttendances(file: File, updateExisting: boolean = false) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<ImportResult>(`/import/attendances/import?update_existing=${updateExisting}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
