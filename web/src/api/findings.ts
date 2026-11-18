import { api, type Schemas } from '@/api/client'

export type Finding = Schemas['Finding']

export function listFindings(caseId: string): Promise<Finding[]> {
  return api(`/api/cases/${encodeURIComponent(caseId)}/findings`)
}
