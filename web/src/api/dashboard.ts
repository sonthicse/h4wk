import { api, type Schemas } from '@/api/client'

export type DashboardStats = Schemas['Dashboard']
export type DayActivity = Schemas['DayActivity']
export type Usage = Schemas['h4wk__api__dashboard__Usage']

// Số liệu tổng hợp (T35): đếm, nghi vấn theo mức/trạng thái, hoạt động 14 ngày, quota, video nổi bật nhất.
export function getDashboard(): Promise<DashboardStats> {
  return api('/api/dashboard?latest_only=true')
}
