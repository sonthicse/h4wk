import { api, type Schemas } from '@/api/client'
import { USE_MOCK_VIDEO_REVIEW } from '@/api/review'

// videos_by_review_status do T49 thêm (chưa có trong schema.d.ts, không chạy gen:api): viết tay, tuỳ chọn tới khi T49 merge.
export type DashboardStats = Schemas['Dashboard'] & { videos_by_review_status?: Schemas['Dashboard']['findings_by_status'] }
export type DayActivity = Schemas['DayActivity']
export type Usage = Schemas['Usage']

// Số liệu tổng hợp (T35): đếm, nghi vấn theo mức/trạng thái, hoạt động 14 ngày, quota, video nổi bật nhất.
export function getDashboard(): Promise<DashboardStats> {
  const p = api<DashboardStats>('/api/dashboard?latest_only=true')
  if (!USE_MOCK_VIDEO_REVIEW) return p
  // GIẢ: thay bằng API T49. Đếm theo video từ dữ liệu giả của hàng đợi.
  return p.then(async (d) => {
    const { mockQueue } = await import('@/api/review.mock')
    const c = { unreviewed: 0, confirmed: 0, rejected: 0, needs_info: 0 }
    for (const q of mockQueue()) c[q.status]++
    return { ...d, videos_by_review_status: c as DashboardStats['findings_by_status'] }
  })
}
