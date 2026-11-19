import { api, type Schemas } from '@/api/client'

export type Finding = Schemas['Finding']

export function listFindings(): Promise<Finding[]> {
  return api('/api/findings')
}
