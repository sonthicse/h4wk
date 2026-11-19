import { api, type Schemas } from '@/api/client'

export type QueueItem = Schemas['QueueItem']
export type ReviewDecision = Schemas['ReviewDecision']
export type ReviewStatus = QueueItem['status']
export type DecisionStatus = ReviewDecision['status']

// Hàng đợi rà soát, sắp theo mức độ rồi thời gian. Mặc định latest_only: chỉ bản thu mới nhất đã phân tích của
// mỗi video, để thu lại một video không làm nghi vấn bị lặp. Video detail truyền latestOnly: false để xem cả bản cũ.
export function listQueue(
  filters: { video?: string; source_kind?: string; status?: string; latestOnly?: boolean } = {},
): Promise<QueueItem[]> {
  const { latestOnly = true, ...rest } = filters
  const params = { ...rest, latest_only: latestOnly ? 'true' : '' }
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][])
  return api(`/api/review/queue${q.size ? `?${q}` : ''}`)
}

// Reject bắt buộc có note (backend trả 422 nếu thiếu).
export function decide(findingId: string, status: DecisionStatus, note = ''): Promise<ReviewDecision> {
  return api(`/api/findings/${encodeURIComponent(findingId)}/decision`, { method: 'POST', body: { status, note } })
}
