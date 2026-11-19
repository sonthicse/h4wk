// Hàm hiển thị nghi vấn dùng chung cho các trang.
import type { Finding } from '@/api/findings'
import type { ReviewStatus } from '@/api/review'

type Severity = Finding['severity']

export const severityVariant: Record<Severity, 'destructive' | 'default' | 'secondary'> = {
  high: 'destructive',
  medium: 'default',
  low: 'secondary',
}

export const statusVariant: Record<ReviewStatus, 'outline' | 'default' | 'secondary'> = {
  unreviewed: 'outline',
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
