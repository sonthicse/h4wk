// Hàm hiển thị nghi vấn dùng chung cho trang Findings và Review queue.
import type { Finding, ReviewStatus, Severity } from '@/mocks/data'

export const severityVariant: Record<Severity, 'destructive' | 'default' | 'secondary'> = {
  high: 'destructive',
  medium: 'default',
  low: 'secondary',
}

export const statusVariant: Record<ReviewStatus, 'outline' | 'default' | 'secondary' | 'destructive'> = {
  pending: 'outline',
  confirmed: 'default',
  rejected: 'secondary',
  needs_info: 'outline',
}

export const severityRank: Record<Severity, number> = { high: 0, medium: 1, low: 2 }

// Các nguồn có mốc thời gian trong video; nguồn còn lại (tiêu đề, mô tả, thumbnail, comment) thì không.
export const timedSources = new Set(['speech', 'ocr', 'visual'])

export function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

export function timeRange(f: Finding) {
  return timedSources.has(f.sourceKind) ? `${formatTime(f.start)}–${formatTime(f.end)}` : '—'
}

export function videoLink(f: Finding) {
  return `/cases/${f.caseId}/videos/${f.videoId}?finding=${f.id}`
}
