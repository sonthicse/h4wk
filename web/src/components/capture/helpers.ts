import type { SourceStatus, VerifyStatus } from '@/api/videos'

// Kích thước dễ đọc: 1536 -> "1.5 KB".
export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes
  let i = -1
  do {
    value /= 1024
    i++
  } while (value >= 1024 && i < units.length - 1)
  return `${value.toFixed(value < 10 ? 2 : 1)} ${units[i]}`
}

// SHA-256 rút gọn: 8 ký tự đầu … 6 ký tự cuối.
export function shortHash(sha256: string) {
  return `${sha256.slice(0, 8)}…${sha256.slice(-6)}`
}

export function sourceStatusVariant(status: SourceStatus) {
  if (status === 'ok') return 'secondary'
  if (status === 'unsupported' || status === 'disabled' || status === 'no_source') return 'outline'
  return 'destructive' // failed, blocked, quota_exceeded, not_found, suspended
}

export function verifyStatusVariant(status: VerifyStatus) {
  if (status === 'OK') return 'secondary'
  if (status === 'unexpected') return 'default'
  return 'destructive' // FAIL, missing
}
