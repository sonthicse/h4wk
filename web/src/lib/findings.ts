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

// Thời điểm t có nằm trong một đoạn của nghi vấn (bỏ đoạn rỗng end = start).
export function inSpans(f: { spans: { start: number; end: number }[] }, t: number) {
  return f.spans.some((s) => s.end > s.start && t >= s.start && t <= s.end)
}

// Nghi vấn có đoạn nào giao với [start, end) không.
export function overlapsSpans(f: { spans: { start: number; end: number }[] }, start: number, end: number) {
  return f.spans.some((s) => s.end > s.start && s.start < end && s.end > start)
}

export function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

// Khoá gộp: bỏ dấu (NFD, bỏ dấu kết hợp, đ -> d), bỏ ký tự điều khiển/ẩn, gộp khoảng trắng, không phân biệt hoa thường.
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
