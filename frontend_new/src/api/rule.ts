import { request } from '@/utils/request'
import type { AlertLevel, PageResponse, Rule, RuleType } from '@/types'

export interface RuleMetricOption {
  value: string
  label: string
  description: string
  supports_time_window?: boolean
  supports_course_type?: boolean
  unit?: string
}

export interface RuleOperatorOption {
  value: string
  label: string
}

export interface RuleTimeWindowOption {
  value: string | null
  label: string
}

export interface RuleTargetTypeOption {
  value: string
  label: string
  description: string
}

export interface RuleCourseTypeOption {
  value: string
  label: string
  description: string
}

export interface RuleQuickTemplate {
  name: string
  code: string
  type: RuleType
  level: AlertLevel
  description?: string
  message_template?: string
  target_type?: string
  conditions: Record<string, any>
}

export interface RuleTemplateResponse {
  metrics: RuleMetricOption[]
  operators: RuleOperatorOption[]
  time_windows: RuleTimeWindowOption[]
  examples: any[]
  special_modes: Array<{ value: string; label: string; description: string }>
  target_types: RuleTargetTypeOption[]
  course_types: RuleCourseTypeOption[]
  quick_templates: RuleQuickTemplate[]
}

export function getRules(params: {
  page?: number
  page_size?: number
  type?: RuleType
  is_active?: boolean
}) {
  return request.get<PageResponse<Rule>>('/rules', { params })
}

export function getRule(id: number) {
  return request.get<Rule>(`/rules/${id}`)
}

export function createRule(data: Partial<Rule>) {
  return request.post<Rule>('/rules', data)
}

export function updateRule(id: number, data: Partial<Rule>) {
  return request.put<Rule>(`/rules/${id}`, data)
}

export function deleteRule(id: number) {
  return request.delete(`/rules/${id}`)
}

export function toggleRule(id: number) {
  return request.post<Rule>(`/rules/${id}/toggle`)
}

export function executeRules() {
  return request.post<{ message: string }>('/rules/execute')
}

export function getRuleTemplates() {
  return request.get<RuleTemplateResponse>('/rules/templates')
}

export function getGrades() {
  return request.get<{ items: Array<{ value: string; label: string }>; total: number }>('/rules/grades')
}

export function getTargetOptions() {
  return request.get<{
    grades: string[]
    classes: Array<{
      id: number
      name: string
      grade: string
      department_name?: string
    }>
  }>('/rules/target-options')
}
