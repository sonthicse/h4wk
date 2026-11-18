import { api, type Schemas } from '@/api/client'

export type Job = Schemas['Job']
export type CollectLevel = Schemas['CollectLevel']

// Dán link video: tạo một job collect → media → analyze (T12).
export function collect(caseId: string, url: string, level: CollectLevel, force = false): Promise<Job> {
  return api(`/api/cases/${encodeURIComponent(caseId)}/collect`, { method: 'POST', body: { url, level, force } })
}

// Job của case, mới nhất trước.
export function listJobs(caseId: string): Promise<Job[]> {
  return api(`/api/jobs?case=${encodeURIComponent(caseId)}`)
}
