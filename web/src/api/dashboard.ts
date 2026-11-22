import { api, type Schemas } from '@/api/client'

export type DashboardStats = Schemas['Dashboard'] & { videos_by_review_status?: Schemas['Dashboard']['findings_by_status'] }
export type DayActivity = Schemas['DayActivity']
export type Usage = Schemas['Usage']

export function getDashboard(): Promise<DashboardStats> {
  return api('/api/dashboard?latest_only=true')
}
