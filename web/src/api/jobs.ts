import { api, type Schemas } from '@/api/client'

export type Job = Schemas['Job']
export type CollectLevel = Schemas['CollectLevel']

// Dán link video: tạo một job collect → media → analyze (T12); link playlist tạo nhiều job.
export function collect(url: string, level: CollectLevel, force = false): Promise<Job[]> {
  return api('/api/collect', { method: 'POST', body: { url, level, force } })
}

// Mọi job, mới nhất trước.
export function listJobs(): Promise<Job[]> {
  return api('/api/jobs')
}

// Phân tích lại bản thu đã xử lý, không thu lại; bỏ trống videoIds là mọi video.
export function reanalyze(videoIds?: string[]): Promise<Job[]> {
  return api('/api/reanalyze', { method: 'POST', body: { video_ids: videoIds ?? null } })
}
