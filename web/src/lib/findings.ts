
import type { Finding } from '@/api/findings'
import type { ReviewStatus } from '@/api/review'

type Severity = Finding['severity']

export const severityVariant: Record<Severity, 'severe' | 'warning' | 'outline'> = {
  high: 'severe',
  medium: 'warning',
  low: 'outline',
}

export const statusVariant: Record<ReviewStatus, 'outline' | 'default' | 'secondary'> = {
  unreviewed: 'outline',
  confirmed: 'default',
  rejected: 'secondary',
  needs_info: 'outline',
}

export const severityRank: Record<Severity, number> = { high: 0, medium: 1, low: 2 }

export const timedSources = new Set(['speech', 'ocr', 'visual'])

export function inSpans(f: { spans: { start: number; end: number }[] }, t: number) {
  return f.spans.some((s) => s.end > s.start && t >= s.start && t <= s.end)
}

export function overlapsSpans(f: { spans: { start: number; end: number }[] }, start: number, end: number) {
  return f.spans.some((s) => s.end > s.start && s.start < end && s.end > start)
}

export function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

export function mergeKey(q: string): string {
  return q
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .replace(/đ/gi, 'd')
    .replace(/[\p{Cc}\p{Cf}]/gu, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

export const showReason = (f: Pick<Finding, 'analyzer'>): boolean => f.analyzer !== 'jev'
