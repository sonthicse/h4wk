import { api, type Schemas } from '@/api/client'

export type Job = Schemas['Job']
export type CollectLevel = Schemas['CollectLevel']

export function collect(url: string, level: CollectLevel, force = false): Promise<Job[]> {
  return api('/api/collect', { method: 'POST', body: { url, level, force } })
}

export function listJobs(): Promise<Job[]> {
  return api('/api/jobs')
}

export function reanalyze(videoIds?: string[]): Promise<Job[]> {
  return api('/api/reanalyze', { method: 'POST', body: { video_ids: videoIds ?? null } })
}
