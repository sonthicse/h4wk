import { api, type Schemas } from '@/api/client'

export type SourcesSettings = Schemas['SourcesSettings']
export type SourceInfo = Schemas['SourceInfo']
export type SourceName = SourceInfo['name']
export type Cap = Schemas['Cap']
export type TestResult = Schemas['TestResult']
export type KeyInfo = Schemas['KeyInfo']

// Thứ tự hiển thị các loại dữ liệu.
export const caps: Cap[] = [
  'video.metadata',
  'channel.metadata',
  'channel.videos',
  'playlist.videos',
  'video.transcripts',
  'video.comments',
  'video.thumbnails',
  'video.media',
]

export const sourceLabel: Record<SourceName, string> = {
  ytdlp: 'yt-dlp',
  youtube_api: 'YouTube Data API',
  supadata: 'Supadata',
}

const source = (name: SourceName) => `/api/settings/sources/${encodeURIComponent(name)}`

export function getSourcesSettings(): Promise<SourcesSettings> {
  return api('/api/settings/sources')
}

export function putSourcesSettings(body: Schemas['SourcesUpdate']): Promise<SourcesSettings> {
  return api('/api/settings/sources', { method: 'PUT', body })
}

export function setSourceKey(name: SourceName, value: string): Promise<KeyInfo> {
  return api(`${source(name)}/key`, { method: 'PUT', body: { value } })
}

export function testSource(name: SourceName): Promise<TestResult> {
  return api(`${source(name)}/test`, { method: 'POST' })
}

export function resumeSource(name: SourceName): Promise<SourceInfo> {
  return api(`${source(name)}/resume`, { method: 'POST' })
}
