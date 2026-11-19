// API watchlist giả cho trang Watchlist (SPEC 10.9). Thay bằng API thật của T30 khi có.
// Check now ở đây không gọi mạng: mỗi kênh có sẵn vài video "chờ phát hiện", lần bấm đầu trả về chúng.

import type { CollectLevel } from '@/mocks/jobs'

// Lấy từ [watchlist] trong config/sources.toml.example.
export const CHECK_INTERVAL_MIN = 2
export const INITIAL_VIDEOS = 10
export const levels: CollectLevel[] = ['metadata', 'text', 'full']

export type LatestVideo = { videoId: string; title: string; publishedAt: string }

export type WatchItem = {
  id: string
  channelId: string
  channelTitle: string
  handle: string
  enabled: boolean
  level: CollectLevel
  addedAt: string
  lastCheckedAt: string | null
  latestVideo: LatestVideo | null
  collectedCount: number
}

export type CheckResult = { newVideos: number; checkedAt: string }

type StoredItem = WatchItem & { pending: LatestVideo[] }

const store: StoredItem[] = [
  {
    id: 'w_012',
    channelId: 'UCZYKmEA2iQOSbyKc6xj5Vfw',
    channelTitle: 'HTV Tin Tức',
    handle: '@HTVTinTuc',
    enabled: true,
    level: 'full',
    addedAt: '2026-11-15T08:00:00+07:00',
    lastCheckedAt: '2026-11-18T09:10:00+07:00',
    latestVideo: { videoId: 'hTv0001aaaa', title: 'Bản tin thời sự sáng 18/11/2026', publishedAt: '2026-11-18T08:45:00+07:00' },
    collectedCount: 23,
    pending: [
      { videoId: 'hTv0002bbbb', title: 'Tin nhanh trưa 18/11: giao thông TP.HCM', publishedAt: '2026-11-18T09:20:00+07:00' },
      { videoId: 'hTv0003cccc', title: 'Bản tin thời sự trưa 18/11/2026', publishedAt: '2026-11-18T09:31:00+07:00' },
    ],
  },
  {
    id: 'w_013',
    channelId: 'UCabsTV34JwALXKGMqHpvUiA',
    channelTitle: 'VTV24',
    handle: '@vtv24',
    enabled: true,
    level: 'full',
    addedAt: '2026-11-15T08:05:00+07:00',
    lastCheckedAt: '2026-11-18T09:10:00+07:00',
    latestVideo: { videoId: 'vTv2400xxxx', title: 'Thời sự 19h VTV1 ngày 17/11/2026', publishedAt: '2026-11-17T20:10:00+07:00' },
    collectedCount: 15,
    pending: [
      { videoId: 'vTv2401yyyy', title: 'Chuyển động 24h trưa 18/11', publishedAt: '2026-11-18T09:25:00+07:00' },
    ],
  },
  {
    id: 'w_014',
    channelId: 'UC4tN0ng24hTinNong00abcd',
    channelTitle: 'Tin Nóng 24h',
    handle: '@tinnong24h',
    enabled: true,
    level: 'full',
    addedAt: '2026-11-16T10:00:00+07:00',
    lastCheckedAt: '2026-11-18T09:10:00+07:00',
    latestVideo: { videoId: 'qWeRtY98765', title: 'SỰ THẬT về ông A mà không ai dám nói', publishedAt: '2026-11-18T07:40:00+07:00' },
    collectedCount: 6,
    pending: [],
  },
  {
    id: 'w_015',
    channelId: 'UCkTsX0ThoiSuX000000wxyz',
    channelTitle: 'Kênh Thời Sự X',
    handle: '@kenhthoisux',
    enabled: true,
    level: 'text',
    addedAt: '2026-11-16T10:05:00+07:00',
    lastCheckedAt: '2026-11-18T09:10:00+07:00',
    latestVideo: { videoId: 'dQw4w9WgXcQ', title: 'Bình luận thời sự tối 17/11', publishedAt: '2026-11-17T21:00:00+07:00' },
    collectedCount: 4,
    pending: [],
  },
  {
    id: 'w_016',
    channelId: 'UC47WI-kZXFf0H_f7pvaNCEQ',
    channelTitle: 'Báo Tuổi Trẻ',
    handle: '@baotuoitre',
    enabled: false,
    level: 'metadata',
    addedAt: '2026-11-15T08:10:00+07:00',
    lastCheckedAt: '2026-11-16T18:00:00+07:00',
    latestVideo: { videoId: 'tTr0001zzzz', title: 'Tin tức tối 16/11/2026', publishedAt: '2026-11-16T17:30:00+07:00' },
    collectedCount: 10,
    pending: [],
  },
]

function delay<T>(value: T, ms = 150): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), ms))
}

// Bỏ trường nội bộ `pending` trước khi trả về giao diện.
function toItem({ pending: _pending, ...item }: StoredItem): WatchItem {
  return item
}

function find(id: string) {
  const item = store.find((w) => w.id === id)
  if (!item) throw new Error('Watchlist item not found.')
  return item
}

export function listWatchItems(): Promise<WatchItem[]> {
  return delay(store.map(toItem))
}

// Nhận link kênh (youtube.com/@handle, youtube.com/channel/UC…) hoặc `@handle`.
// Với `@handle`, channel ID chỉ biết sau khi backend tra kênh nên để null.
export function parseChannelInput(input: string): { handle: string; channelId: string | null } | null {
  const s = input.trim()
  const handle = s.match(/^(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/)?(@[\w.-]{3,30})\/?$/)
  if (handle) return { handle: handle[1], channelId: null }
  const channel = s.match(/^(?:https?:\/\/)?(?:www\.|m\.)?youtube\.com\/channel\/(UC[\w-]{22})\/?$/)
  if (channel) return { handle: '', channelId: channel[1] }
  return null
}

export function addWatchItem(input: string, level: CollectLevel): Promise<WatchItem> {
  const parsed = parseChannelInput(input)
  if (!parsed) return Promise.reject(new Error('Enter a channel link or an @handle.'))
  const exists = store.some(
    (w) => w.channelId === parsed.channelId || (parsed.handle && w.handle.toLowerCase() === parsed.handle.toLowerCase()),
  )
  if (exists) return Promise.reject(new Error('This channel is already in the watchlist.'))

  const now = new Date().toISOString()
  const channelId = parsed.channelId ?? `UCmock${Date.now()}`
  const item: StoredItem = {
    id: `w_${Date.now()}`,
    channelId,
    // Backend thật lấy tên kênh từ bản thu hồ sơ kênh; ở đây tạm dùng handle hoặc channel ID.
    channelTitle: parsed.handle ? parsed.handle.slice(1) : channelId,
    handle: parsed.handle,
    enabled: true,
    level,
    addedAt: now,
    lastCheckedAt: now,
    latestVideo: null,
    collectedCount: 0,
    pending: [],
  }
  store.push(item)
  return delay(toItem(item), 400)
}

export function updateWatchItem(id: string, patch: Partial<Pick<WatchItem, 'enabled' | 'level'>>): Promise<WatchItem> {
  const item = find(id)
  Object.assign(item, patch)
  return delay(toItem(item))
}

export function removeWatchItem(id: string): Promise<void> {
  const i = store.findIndex((w) => w.id === id)
  if (i >= 0) store.splice(i, 1)
  return delay(undefined)
}

// Check now: backend thật đọc RSS và uploads playlist của YouTube API (SPEC 10.9, spike T2).
export function checkNow(id: string): Promise<CheckResult> {
  const item = find(id)
  const found = item.pending.splice(0)
  item.lastCheckedAt = new Date().toISOString()
  if (found.length > 0) {
    item.latestVideo = found[found.length - 1]
    item.collectedCount += found.length
  }
  return delay({ newVideos: found.length, checkedAt: item.lastCheckedAt }, 1500)
}
