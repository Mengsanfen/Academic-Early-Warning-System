import { request } from '@/utils/request'
import type { 
  PageResponse, 
  Alert, 
  AlertDetail, 
  AlertStatus, 
  AlertLevel 
} from '@/types'

// 获取预警列表
export function getAlerts(params: {
  page?: number
  page_size?: number
  status?: AlertStatus
  level?: AlertLevel
  class_id?: number
  student_name?: string
}) {
  return request.get<PageResponse<Alert>>('/alerts', { params })
}

// 获取预警详情
export function getAlert(id: number) {
  return request.get<AlertDetail>(`/alerts/${id}`)
}

// 获取预警统计
export function getAlertStatistics() {
  return request.get<{
    total: number
    by_status: Record<string, number>
    by_level: Record<string, number>
  }>('/alerts/statistics')
}

// 处理预警
export function handleAlert(id: number, data: { action: string; result?: string }) {
  return request.post<{ message: string; record_id: number }>(`/alerts/${id}/handle`, data)
}

// 更新预警状态
export function updateAlertStatus(id: number, status: AlertStatus) {
  return request.put<{ message: string }>(`/alerts/${id}/status`, null, {
    params: { status }
  })
}
