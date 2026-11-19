// API giả cho trang Dashboard (T31 dòng sự kiện, T35 số liệu). Thay bằng `api/dashboard.py` khi có.
// Dòng sự kiện tự sinh sự kiện mới theo thời gian, nên poll mỗi 5 giây sẽ thấy feed cập nhật.
import type { JobStatus } from '@/mocks/jobs'
import { findings, type Category, type ReviewStatus, type Severity } from '@/mocks/data'
import { findVideo } from '@/mocks/videos'

export type DayActivity = { date: string; captures: number; findings: number }

export type DashboardStats = {
  channelCount: number
  videoCount: number
  captureCount: number
  findingsBySeverity: Record<Severity, number>
  findingsByStatus: Record<ReviewStatus, number>
  activity: DayActivity[]
  featured: FeaturedVideo | null
  // Quota YouTube Data API đếm theo ngày, reset lúc nửa đêm giờ Thái Bình Dương; credit Supadata đếm theo tháng (SPEC 10.3).
  youtubeQuota: { used: number; limit: number }
  supadataCredits: { used: number; limit: number }
}

// Video nổi bật nhất: video có nhiều nghi vấn nặng nhất (xem featuredVideo bên dưới).
export type FeaturedVideo = {
  videoId: string
  title: string
  channel: string
  publishedAt: string | null
  viewCount: number | null
  findingsBySeverity: Record<Severity, number>
  pending: number
  // Nghi vấn nặng nhất của video, để hiện trích dẫn.
  top: { id: string; quote: string; category: Category; severity: Severity; start: number; timed: boolean }
}

export type FeedEvent = {
  id: string
  at: string
  kind: 'new_video' | 'job_done' | 'job_failed' | 'review'
  message: string
  videoId?: string
  videoTitle?: string
  job?: { id: string; status: JobStatus }
  error?: string
}

const MINUTE = 60_000
const pageLoadedAt = Date.now()
const ago = (minutes: number) => new Date(pageLoadedAt - minutes * MINUTE).toISOString()

// Video mới mà watchlist "phát hiện" sau khi trang mở. Kênh tin tức không nhắc đối tượng nên không sinh nghi vấn (SPEC 8, màn 3).
const upcoming = [
  { channel: 'HTV Tin Tức', videoId: 'hTvN1118a01', title: 'Bản tin trưa 18/11: Giao thông TP.HCM sau cơn mưa lớn' },
  { channel: 'VTV24', videoId: 'vTv24x18b02', title: 'Thời sự 12h: Giá xăng dầu điều chỉnh từ 15h chiều nay' },
  { channel: 'HTV Tin Tức', videoId: 'hTvN1118c03', title: 'Người dân phường Bến Thành góp ý chỉnh trang vỉa hè' },
  { channel: 'VTV24', videoId: 'vTv24x18d04', title: 'TRỰC TIẾP: Họp báo Chính phủ thường kỳ tháng 11', fails: true },
  { channel: 'VTV24', videoId: 'vTv24x18e05', title: 'Dự báo thời tiết 18/11: Bắc Bộ đón không khí lạnh' },
  { channel: 'HTV Tin Tức', videoId: 'hTvN1118f06', title: 'Khánh thành cầu vượt nút giao An Phú' },
  { channel: 'HTV Tin Tức', videoId: 'hTvN1118g07', title: 'Bản tin chiều 18/11: Chợ Bến Thành chuẩn bị mùa Tết' },
  { channel: 'VTV24', videoId: 'vTv24x18h08', title: 'Cảnh báo thủ đoạn lừa đảo qua tin nhắn ngân hàng' },
]

const FIRST_DETECTION_MS = 6_000 // video đầu tiên xuất hiện ngay sau khi mở trang
const DETECTION_EVERY_MS = 30_000
const QUEUE_MS = 3_000
const JOB_MS = 15_000 // thời gian giả để xử lý xong một video

function detectedSoFar() {
  const elapsed = Date.now() - pageLoadedAt - FIRST_DETECTION_MS
  if (elapsed < 0) return []
  return upcoming.slice(0, Math.floor(elapsed / DETECTION_EVERY_MS) + 1).map((v, i) => ({
    ...v,
    detectedAt: pageLoadedAt + FIRST_DETECTION_MS + i * DETECTION_EVERY_MS,
  }))
}

function jobStatus(startedAt: number, fails = false): JobStatus {
  const elapsed = Date.now() - startedAt
  if (elapsed < QUEUE_MS) return 'queued'
  if (elapsed < QUEUE_MS + JOB_MS) return 'running'
  return fails ? 'failed' : 'done'
}

// Sự kiện có sẵn: khớp job j_001, j_002 ở mocks/jobs.ts và quyết định rà soát trong mocks/data.ts.
const seedEvents: FeedEvent[] = [
  {
    id: 'e_008',
    at: ago(12),
    kind: 'review',
    message: 'user:thi confirmed finding f_008',
    videoId: 'qWeRtY98765',
    videoTitle: 'SỰ THẬT về ông A mà không ai dám nói',
  },
  {
    id: 'e_007',
    at: ago(18),
    kind: 'review',
    message: 'user:thi rejected finding f_004: Phê bình dựa trên số liệu công khai',
    videoId: 'aBcD1234xyz',
    videoTitle: 'Phân tích báo cáo tài chính quý 3',
  },
  {
    id: 'e_006',
    at: ago(25),
    kind: 'review',
    message: 'user:minh marked finding f_003 as needs_info',
    videoId: 'aBcD1234xyz',
    videoTitle: 'Phân tích báo cáo tài chính quý 3',
  },
  {
    id: 'e_005',
    at: ago(52),
    kind: 'job_done',
    message: 'Job j_002 finished',
    videoId: 'aBcD1234xyz',
    videoTitle: 'Phân tích báo cáo tài chính quý 3',
    job: { id: 'j_002', status: 'done' },
  },
  {
    id: 'e_004',
    at: ago(95),
    kind: 'new_video',
    message: 'New video detected on HTV Tin Tức',
    videoId: 'hTvN1118z00',
    videoTitle: 'Bản tin sáng 18/11: Khởi công tuyến metro số 2',
    job: { id: 'j_w003', status: 'done' },
  },
  {
    id: 'e_003',
    at: ago(120),
    kind: 'job_failed',
    message: 'Job j_001 failed',
    job: { id: 'j_001', status: 'failed' },
    error: "yt-dlp: Private video. Sign in if you've been granted access to this video.",
  },
  {
    id: 'e_002',
    at: ago(170),
    kind: 'new_video',
    message: 'New video detected on VTV24',
    videoId: 'vTv24x18y00',
    videoTitle: 'Thời sự 6h sáng 18/11',
    job: { id: 'j_w002', status: 'done' },
  },
  {
    id: 'e_101',
    at: ago(300),
    kind: 'review',
    message: 'user:thi confirmed finding f_005',
    videoId: 'zzZZ9876abc',
    videoTitle: 'Livestream hỏi đáp',
  },
]

// Mỗi video watchlist mới sinh hai sự kiện: phát hiện (kèm trạng thái job hiện tại) và job xong/lỗi.
function liveEvents(): FeedEvent[] {
  return detectedSoFar().flatMap((v, i) => {
    const jobId = `j_w${100 + i}`
    const status = jobStatus(v.detectedAt, v.fails)
    const video = { videoId: v.videoId, videoTitle: v.title }
    const events: FeedEvent[] = [
      {
        id: `e_live_${i}_detected`,
        at: new Date(v.detectedAt).toISOString(),
        kind: 'new_video',
        message: `New video detected on ${v.channel}`,
        ...video,
        job: { id: jobId, status },
      },
    ]
    if (status === 'done' || status === 'failed') {
      events.push({
        id: `e_live_${i}_${status}`,
        at: new Date(v.detectedAt + QUEUE_MS + JOB_MS).toISOString(),
        kind: status === 'done' ? 'job_done' : 'job_failed',
        message: `Job ${jobId} ${status === 'done' ? 'finished' : 'failed'}`,
        ...video,
        job: { id: jobId, status },
        error: v.fails ? 'yt-dlp: This live event will begin in a few moments.' : undefined,
      })
    }
    return events
  })
}

function delay<T>(value: T): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), 150))
}

export function listEvents(): Promise<FeedEvent[]> {
  const all = [...liveEvents(), ...seedEvents]
  return delay(all.sort((a, b) => b.at.localeCompare(a.at)))
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

const SEVERITY_WEIGHT: Record<Severity, number> = { high: 3, medium: 2, low: 1 }

// Chấm điểm mỗi video theo nghi vấn: high = 3, medium = 2, low = 1; bằng điểm thì video nhiều lượt xem hơn đứng trước.
// Nghi vấn đã bị Reject không tính, vì analyst đã kết luận là báo nhầm.
function featuredVideo(): FeaturedVideo | null {
  const live = findings.filter((f) => f.status !== 'rejected')
  const ids = [...new Set(live.map((f) => f.videoId))]
  if (ids.length === 0) return null
  const score = (id: string) => live.filter((f) => f.videoId === id).reduce((s, f) => s + SEVERITY_WEIGHT[f.severity], 0)
  const views = (id: string) => findVideo(id)?.viewCount ?? 0
  const best = ids.sort((a, b) => score(b) - score(a) || views(b) - views(a))[0]

  const list = live.filter((f) => f.videoId === best)
  const top = [...list].sort((a, b) => SEVERITY_WEIGHT[b.severity] - SEVERITY_WEIGHT[a.severity])[0]
  const video = findVideo(best)
  return {
    videoId: best,
    title: video?.title ?? top.videoTitle,
    channel: video?.channel ?? top.channel,
    publishedAt: video?.publishedAt ?? null,
    viewCount: video?.viewCount ?? null,
    findingsBySeverity: {
      high: list.filter((f) => f.severity === 'high').length,
      medium: list.filter((f) => f.severity === 'medium').length,
      low: list.filter((f) => f.severity === 'low').length,
    },
    pending: list.filter((f) => f.status === 'pending' || f.status === 'needs_info').length,
    top: {
      id: top.id,
      quote: top.quote,
      category: top.category,
      severity: top.severity,
      start: top.start,
      timed: ['speech', 'ocr', 'visual'].includes(top.sourceKind),
    },
  }
}

export function getDashboard(): Promise<DashboardStats> {
  const count = <K extends string>(keys: K[], pick: (f: (typeof findings)[number]) => K) =>
    Object.fromEntries(keys.map((k) => [k, findings.filter((f) => pick(f) === k).length])) as Record<K, number>

  // Video watchlist đã xử lý xong được cộng vào số video, số lần thu và cột hôm nay.
  const processed = liveEvents().filter((e) => e.kind === 'job_done').length
  const series = activitySeries
  const activity = lastDays(14).map((date, i) => ({
    date,
    captures: series.captures[i] + (i === 13 ? processed : 0),
    findings: series.findings[i],
  }))

  return delay({
    channelCount: CHANNEL_COUNT,
    videoCount: BASE_VIDEO_COUNT + processed,
    captureCount: activity.reduce((sum, d) => sum + d.captures, 0),
    findingsBySeverity: count(['high', 'medium', 'low'], (f) => f.severity),
    findingsByStatus: count(['pending', 'confirmed', 'rejected', 'needs_info'], (f) => f.status),
    activity,
    featured: featuredVideo(),
    youtubeQuota: { used: 1_243 + processed * 3, limit: 10_000 },
    supadataCredits: { used: 37, limit: 100 },
  })
}
