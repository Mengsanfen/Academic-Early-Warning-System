import { request } from '@/utils/request'
import type { DashboardOverview, TrendData, DistributionData } from '@/types'

// 获取仪表盘概览
export function getOverview() {
  return request.get<DashboardOverview>('/dashboard/overview')
}

// 获取预警趋势
export function getTrend(days: number = 7) {
  return request.get<TrendData>('/dashboard/trend', { params: { days } })
}

// 获取预警分布
export function getDistribution() {
  return request.get<DistributionData>('/dashboard/distribution')
}
