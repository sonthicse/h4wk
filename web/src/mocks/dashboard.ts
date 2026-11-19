// API giả cho số liệu Dashboard (T35). Thay bằng `api/dashboard.py` khi có. Dòng sự kiện đã dùng API thật (api/watchlist.ts).
import { findings, type ReviewStatus, type Severity } from '@/mocks/data'

export type DayActivity = { date: string; captures: number; findings: number }

export type DashboardStats = {
  channelCount: number
  videoCount: number
  captureCount: number
  findingsBySeverity: Record<Severity, number>
  findingsByStatus: Record<ReviewStatus, number>
  activity: DayActivity[]
  // Quota YouTube Data API đếm theo ngày, reset lúc nửa đêm giờ Thái Bình Dương; credit Supadata đếm theo tháng (SPEC 10.3).
  youtubeQuota: { used: number; limit: number }
  supadataCredits: { used: number; limit: number }
}

const MINUTE = 60_000

function delay<T>(value: T): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), 150))
}

// Số lần thu và nghi vấn mỗi ngày trong 14 ngày gần nhất, cũ trước mới sau. Tổng khớp với số nghi vấn trong mocks/data.ts.
const activitySeries = {
  captures: [0, 1, 0, 2, 1, 0, 3, 1, 0, 2, 1, 4, 4, 2],
  findings: [0, 0, 0, 1, 0, 0, 2, 0, 0, 1, 0, 3, 3, 2],
}

const CHANNEL_COUNT = 5
const BASE_VIDEO_COUNT = 17

function lastDays(n: number) {
  return Array.from({ length: n }, (_, i) => new Date(Date.now() - (n - 1 - i) * 24 * 60 * MINUTE).toISOString())
}

export function getDashboard(): Promise<DashboardStats> {
  const count = <K extends string>(keys: K[], pick: (f: (typeof findings)[number]) => K) =>
    Object.fromEntries(keys.map((k) => [k, findings.filter((f) => pick(f) === k).length])) as Record<K, number>

  const series = activitySeries
  const activity = lastDays(14).map((date, i) => ({
    date,
    captures: series.captures[i],
    findings: series.findings[i],
  }))

  return delay({
    channelCount: CHANNEL_COUNT,
    videoCount: BASE_VIDEO_COUNT,
    captureCount: activity.reduce((sum, d) => sum + d.captures, 0),
    findingsBySeverity: count(['high', 'medium', 'low'], (f) => f.severity),
    findingsByStatus: count(['pending', 'confirmed', 'rejected', 'needs_info'], (f) => f.status),
    activity,
    youtubeQuota: { used: 1_243, limit: 10_000 },
    supadataCredits: { used: 37, limit: 100 },
  })
}
