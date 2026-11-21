import { api, type Schemas } from '@/api/client'

// videos_by_review_status do T49 thêm (chưa có trong schema.d.ts, không chạy gen:api): viết tay, tuỳ chọn tới khi T49 merge.
export type DashboardStats = Schemas['Dashboard'] & { videos_by_review_status?: Schemas['Dashboard']['findings_by_status'] }
export type DayActivity = Schemas['DayActivity']
export type Usage = Schemas['Usage']

// Số liệu tổng hợp (T35): đếm, nghi vấn theo mức/trạng thái, hoạt động 14 ngày, quota, video nổi bật nhất.
export function getDashboard(): Promise<DashboardStats> {
  return api('/api/dashboard?latest_only=true')
}
