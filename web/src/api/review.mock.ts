// GIẢ: thay bằng API T49. Dữ liệu và quyết định chỉ nằm trong bộ nhớ của trang.
import type { VideoQueueItem, VideoReviewDecision, VideoVerdictDetail, VideoDecisionStatus } from '@/api/review'

const verdict = (id: string, violation: 'yes' | 'uncertain', sev: 'high' | 'medium', cats: ('incitement' | 'insult')[]) => ({
  run_id: `run-${id}`,
  video_id: id,
  capture: '20261120T220000',
  violation,
  categories: cats,
  severity: sev,
  confidence: violation === 'yes' ? ('likely' as const) : ('unverified' as const),
  summary: violation === 'yes' ? 'Băng rôn kêu gọi lật đổ chính quyền xuất hiện suốt video.' : 'Chưa có kết luận tự động: quota',
  finding_ids: [`f-${id}-1`],
  model: null,
  at: '2026-11-21T00:00:00+07:00',
})

const decisions: Record<string, VideoReviewDecision[]> = {}

export function mockQueue(): VideoQueueItem[] {
  return [
    ['1RUJ_6eruwA', 'yes', 'high', ['incitement']],
    ['mockvideo02', 'uncertain', 'medium', ['insult']],
  ].map(([id, v, s, c]) => {
    const d = decisions[id as string] ?? []
    return {
      video: { id: id as string, title: `Video ${id}`, channel: 'Mock channel' },
      capture: '20261120T220000',
      run_id: `run-${id}`,
      verdict: verdict(id as string, v as 'yes', s as 'high', c as ['incitement']),
      status: d[0]?.status ?? 'unreviewed',
      finding_count: 3,
      decisions: d,
    }
  })
}

export function mockDetail(videoId: string): VideoVerdictDetail | null {
  const it = mockQueue().find((q) => q.video.id === videoId)
  return it ? { verdict: it.verdict, status: it.status, decisions: it.decisions, findings: [] } : null
}

export function mockDecide(videoId: string, runId: string, status: VideoDecisionStatus, note: string): VideoReviewDecision {
  const d = { video_id: videoId, run_id: runId, status, by: 'mock', at: new Date().toISOString(), note }
  decisions[videoId] = [d, ...(decisions[videoId] ?? [])]
  return d
}
