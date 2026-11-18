import { api, type Schemas } from '@/api/client'

export type CaseSummary = Schemas['CaseSummary']
export type CaseFile = Schemas['CaseFile']
export type Entity = Schemas['Entity']

export function listCases(): Promise<CaseSummary[]> {
  return api('/api/cases')
}

export function getCase(caseId: string): Promise<CaseFile> {
  return api(`/api/cases/${encodeURIComponent(caseId)}`)
}

export function createCase(title: string, goal: string): Promise<CaseFile> {
  return api('/api/cases', { method: 'POST', body: { title, goal } })
}

export function addEntity(caseId: string, name: string): Promise<Entity> {
  return api(`/api/cases/${encodeURIComponent(caseId)}/entities`, {
    method: 'POST',
    body: { name, aliases: [], abbreviations: [] },
  })
}
