import { request } from '@/utils/request'
import type { PageResponse, Rule, RuleType, AlertLevel } from '@/types'

// 获取规则列表
export function getRules(params: {
  page?: number
  page_size?: number
  type?: RuleType
  is_active?: boolean
}) {
  return request.get<PageResponse<Rule>>('/rules', { params })
}

// 获取规则详情
export function getRule(id: number) {
  return request.get<Rule>(`/rules/${id}`)
}

// 创建规则
export function createRule(data: Partial<Rule>) {
  return request.post<Rule>('/rules', data)
}

// 更新规则
export function updateRule(id: number, data: Partial<Rule>) {
  return request.put<Rule>(`/rules/${id}`, data)
}

// 删除规则
export function deleteRule(id: number) {
  return request.delete(`/rules/${id}`)
}

// 切换规则状态
export function toggleRule(id: number) {
  return request.post<Rule>(`/rules/${id}/toggle`)
}

// 执行规则
export function executeRules() {
  return request.post<{ message: string }>('/rules/execute')
}
