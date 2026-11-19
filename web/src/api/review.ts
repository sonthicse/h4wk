import { api, type Schemas } from '@/api/client'

export type QueueItem = Schemas['QueueItem']
export type ReviewDecision = Schemas['ReviewDecision']
export type ReviewStatus = QueueItem['status']
export type DecisionStatus = ReviewDecision['status']

// Hàng đợi rà soát: nghi vấn của lần phân tích mới nhất mỗi bản thu, sắp theo mức độ rồi thời gian.
export function listQueue(filters: { video?: string; source_kind?: string; status?: string } = {}): Promise<QueueItem[]> {
  const q = new URLSearchParams(Object.entries(filters).filter(([, v]) => v) as [string, string][])
  return api(`/api/review/queue${q.size ? `?${q}` : ''}`)
}

// Reject bắt buộc có note (backend trả 422 nếu thiếu).
export function decide(findingId: string, status: DecisionStatus, note = ''): Promise<ReviewDecision> {
  return api(`/api/findings/${encodeURIComponent(findingId)}/decision`, { method: 'POST', body: { status, note } })
}
