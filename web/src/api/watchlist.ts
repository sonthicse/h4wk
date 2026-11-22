import { api, type Schemas } from '@/api/client'
import type { CollectLevel } from '@/api/jobs'

export type WatchItem = Schemas['WatchItem']
export type WatchEvent = Schemas['Event']
export type CheckResult = Schemas['CheckResult']

export const levels: CollectLevel[] = ['metadata', 'text', 'full']

const item = (id: string) => `/api/watchlist/${encodeURIComponent(id)}`

export function listWatchItems(): Promise<WatchItem[]> {
  return api('/api/watchlist')
}

export function addWatchItem(url: string, level: CollectLevel): Promise<WatchItem> {
  return api('/api/watchlist', { method: 'POST', body: { url: url.trim(), level } })
}

export function updateWatchItem(id: string, patch: { enabled?: boolean; level?: CollectLevel }): Promise<WatchItem> {
  return api(item(id), { method: 'PATCH', body: patch })
}

export function removeWatchItem(id: string): Promise<void> {
  return api(item(id), { method: 'DELETE' })
}

export function checkNow(id: string): Promise<CheckResult> {
  return api(`${item(id)}/check`, { method: 'POST' })
}

export function listEvents(limit = 50): Promise<WatchEvent[]> {
  return api(`/api/events?limit=${limit}`)
}

export function isChannelInput(input: string): boolean {
  const s = input.trim()
  return /\/(@|channel\/|c\/|user\/)/.test(s) || s.startsWith('@') || /^UC[\w-]{22}$/.test(s)
}
