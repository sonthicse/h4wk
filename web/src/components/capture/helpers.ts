import type { SourceStatus, VerifyStatus } from '@/api/videos'

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

export function shortHash(sha256: string) {
  return `${sha256.slice(0, 8)}…${sha256.slice(-6)}`
}

export function sourceStatusVariant(status: SourceStatus) {
  if (status === 'ok') return 'secondary'
  if (status === 'unsupported' || status === 'disabled' || status === 'no_source') return 'outline'
  return 'destructive'
}

export function verifyStatusVariant(status: VerifyStatus) {
  if (status === 'OK') return 'secondary'
  if (status === 'unexpected') return 'default'
  return 'destructive'
}
