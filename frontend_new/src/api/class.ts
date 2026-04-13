import { request } from '@/utils/request'

export interface ClassOption {
  id: number
  name: string
  grade: string
  department_id?: number
  department_name?: string
  student_count?: number
}

export function getClasses(params?: { department_id?: number }) {
  return request.get<{ items: ClassOption[]; total: number }>('/classes', { params })
}
