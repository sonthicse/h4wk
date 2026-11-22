import { api, ApiError, type Schemas } from '@/api/client'
import type { QueueItem } from '@/api/review'

export type VideoSummary = Schemas['VideoSummary']
export type VideoDetail = Schemas['VideoDetail']
export type CaptureSummary = Schemas['CaptureSummary']
export type Timeline = Schemas['Timeline']
export type Transcript = Schemas['Transcript']
export type TranscriptKind = Transcript['kind']
export type VideoComment = Schemas['Comment']
export type CaptureDetail = Schemas['CaptureDetail']
export type Manifest = Schemas['Manifest']
export type SourceCall = Schemas['SourceCall']
export type SourceStatus = SourceCall['status']
export type VerifyResult = Schemas['VerifyResult']
export type VerifyFile = Schemas['FileResult']
export type VerifyStatus = Schemas['FileStatus']
export type Severity = Schemas['Severity']

const vid = (id: string) => `/api/videos/${encodeURIComponent(id)}`
const cap = (capture?: string) => (capture ? `?capture=${encodeURIComponent(capture)}` : '')

async function orNull<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
}

export function listVideos(): Promise<VideoSummary[]> {
  return api('/api/videos?latest_only=true')
}

export function getVideo(id: string): Promise<VideoDetail | null> {
  return orNull(api(vid(id)))
}

export function getTimeline(id: string, capture?: string): Promise<Timeline | null> {
  return orNull(api(`${vid(id)}/timeline${cap(capture)}`))
}

export function listTranscripts(id: string, capture?: string): Promise<Transcript[]> {
  return api(`${vid(id)}/transcripts${cap(capture)}`)
}

export function listComments(id: string, capture?: string): Promise<VideoComment[]> {
  return api(`${vid(id)}/comments${cap(capture)}`)
}

export function getCapture(id: string, capture: string): Promise<CaptureDetail | null> {
  return orNull(api(`${vid(id)}/captures/${encodeURIComponent(capture)}`))
}

export function verifyCapture(id: string, capture: string): Promise<VerifyResult> {
  return api(`${vid(id)}/captures/${encodeURIComponent(capture)}/verify`, { method: 'POST' })
}

export const mediaUrl = (id: string, capture?: string) => `${vid(id)}/media${cap(capture)}`

export const frameUrl = (id: string, frame: string, capture?: string) =>
  `${vid(id)}/frames/${encodeURIComponent(frame.split('/').pop() ?? frame)}${cap(capture)}`

export const captureFileUrl = (id: string, capture: string, path: string) =>
  `${vid(id)}/captures/${encodeURIComponent(capture)}/files/${path.split('/').map(encodeURIComponent).join('/')}`

export type VideoFinding = {
  id: string
  capture: string
  sourceKind: Schemas['SourceKind']
  start: number | null
  end: number | null

  spans: { start: number; end: number }[]
  quote: string
  severity: Severity
  category: Schemas['Finding']['category']
  entity: string | null | undefined
  frame: string | null
  commentId: string | null
  triggers: Schemas['Finding']['triggers']
}

export function toVideoFinding({ finding: f }: QueueItem): VideoFinding {
  return {
    id: f.id,
    capture: f.capture,
    sourceKind: f.source_kind,
    start: f.start ?? null,
    end: f.end ?? null,
    spans: f.occurrences?.length
      ? f.occurrences.map((o) => ({ start: o.start, end: o.end }))
      : f.start != null
        ? [{ start: f.start, end: f.end ?? f.start }]
        : [],
    quote: f.quote ?? '',
    severity: f.severity,
    category: f.category,
    entity: f.entity,
    frame: f.frame ?? null,
    commentId: f.comment_id ?? null,
    triggers: f.triggers ?? [],
  }
}
