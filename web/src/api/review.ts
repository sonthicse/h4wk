import { api, ApiError, type Schemas } from '@/api/client'

export type QueueItem = Schemas['QueueItem']
export type ReviewDecision = Schemas['ReviewDecision']
export type ReviewStatus = QueueItem['status']
export type DecisionStatus = ReviewDecision['status']

export function listQueue(
  filters: { video?: string; source_kind?: string; status?: string; latestOnly?: boolean } = {},
): Promise<QueueItem[]> {
  const { latestOnly = true, ...rest } = filters
  const params = { ...rest, latest_only: latestOnly ? 'true' : '' }
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][])
  return api(`/api/review/queue${q.size ? `?${q}` : ''}`)
}

export function decide(findingId: string, status: DecisionStatus, note = ''): Promise<ReviewDecision> {
  return api(`/api/findings/${encodeURIComponent(findingId)}/decision`, { method: 'POST', body: { status, note } })
}

type Category = Schemas['Category']
export type VideoVerdict = {
  run_id: string
  video_id: string
  capture: string
  violation: 'yes' | 'no' | 'uncertain'
  categories: Category[]
  severity: Schemas['Severity'] | null
  confidence: Schemas['Confidence']
  summary: string
  finding_ids: string[]
  model: Schemas['ModelRef'] | null
  at: string
}
export type VideoDecisionStatus = 'confirmed' | 'rejected' | 'needs_info'
export type VideoReviewStatus = 'unreviewed' | VideoDecisionStatus
export type VideoReviewDecision = {
  video_id: string
  run_id: string
  status: VideoDecisionStatus
  by: string
  at: string
  note: string
}
export type VideoQueueItem = {
  video: Schemas['VideoRef']
  capture: string
  run_id: string
  verdict: VideoVerdict
  status: VideoReviewStatus
  finding_count: number
  decisions: VideoReviewDecision[]
}
export type VideoVerdictDetail = {
  verdict: VideoVerdict
  status: VideoReviewStatus
  decisions: VideoReviewDecision[]
  findings: Schemas['Finding'][]
}

export async function listVideoQueue(status?: string): Promise<VideoQueueItem[]> {
  const q = new URLSearchParams({ latest_only: 'true', ...(status ? { status } : {}) })
  return api(`/api/review/videos?${q}`)
}

export async function getVerdict(videoId: string): Promise<VideoVerdictDetail | null> {
  try {
    return await api(`/api/videos/${encodeURIComponent(videoId)}/verdict`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
}

export async function decideVideo(
  videoId: string,
  runId: string,
  status: VideoDecisionStatus,
  note = '',
): Promise<VideoReviewDecision> {
  return api(`/api/videos/${encodeURIComponent(videoId)}/decision`, {
    method: 'POST',
    body: { status, note, run_id: runId },
  })
}
