import { useQuery } from '@tanstack/react-query'
import { ExternalLinkIcon } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import type { Finding } from '@/api/findings'
import { listQueue } from '@/api/review'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatTime, severityVariant } from '@/lib/findings'
import { cn } from '@/lib/utils'

type Severity = Finding['severity']

const WEIGHT: Record<Severity, number> = { high: 3, medium: 2, low: 1 }
const LEAD_S = 2

// Nghi vấn của video nổi bật (backend chọn ở /api/dashboard: high 3, medium 2, low 1, bỏ đã Reject), nặng nhất trước.
function videoFindings(findings: Finding[], videoId: string) {
  return findings
    .filter((f) => f.video_id === videoId)
    .sort((a, b) => WEIGHT[b.severity] - WEIGHT[a.severity] || (a.start ?? 0) - (b.start ?? 0))
}

// Trình phát nhúng của YouTube (bản nocookie), tự phát không tiếng từ giây `start`.
// Khi backend có luồng video proxy (T26) thì thay bằng <video> phát từ bản thu.
function EmbeddedPlayer({ videoId, start }: { videoId: string; start: number }) {
  const src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(videoId)}?autoplay=1&mute=1&start=${start}&rel=0`
  return (
    <iframe
      key={`${videoId}-${start}`}
      src={src}
      title="Top video"
      className="aspect-video w-full rounded-lg bg-black"
      allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
      allowFullScreen
    />
  )
}

export default function FeaturedVideoCard({ topVideoId }: { topVideoId: string | null }) {
  const findings = useQuery({ queryKey: ['review-queue'], queryFn: () => listQueue(), refetchInterval: 30_000 })
  const live = findings.data?.filter((it) => it.status !== 'rejected').map((it) => it.finding)
  const list = live && topVideoId ? videoFindings(live, topVideoId) : []
  const top = topVideoId && list.length > 0 ? { videoId: topVideoId, findings: list } : null
  const video = findings.data?.find((it) => it.finding.video_id === top?.videoId)?.video
  const [picked, setPicked] = useState<string | null>(null)

  if (!top) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top video</CardTitle>
          <CardDescription>
            {findings.isPending
              ? 'Loading…'
              : findings.error
                ? `Could not load findings: ${findings.error.message}`
                : 'No findings yet. Collect a video and the one with the most serious findings plays here.'}
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  // Nghi vấn đang phát: mặc định là nghi vấn nặng nhất; bấm nghi vấn khác để nhảy tới đó.
  const current = top.findings.find((f) => f.id === picked) ?? top.findings[0]
  const start = Math.max(0, Math.floor((current.start ?? 0) - LEAD_S))
  const count = (s: Severity) => top.findings.filter((f) => f.severity === s).length

  return (
    <Card>
      <CardHeader>
        <CardDescription>Top video · most serious findings</CardDescription>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="line-clamp-2 text-lg">{video?.title ?? top.videoId}</CardTitle>
            {video?.channel && <p className="text-sm text-muted-foreground">{video.channel}</p>}
          </div>
          <div className="flex shrink-0 items-center gap-2 text-sm">
            {(['high', 'medium', 'low'] as const).map(
              (s) =>
                count(s) > 0 && (
                  <Badge key={s} variant={severityVariant[s]}>
                    {count(s)} {s}
                  </Badge>
                ),
            )}
            <a
              href={`https://www.youtube.com/watch?v=${encodeURIComponent(top.videoId)}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-primary hover:underline"
            >
              YouTube <ExternalLinkIcon className="size-3.5" />
            </a>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <EmbeddedPlayer videoId={top.videoId} start={start} />
        <ul className="space-y-1">
          {top.findings.map((f) => (
            <li key={f.id}>
              <button
                type="button"
                onClick={() => setPicked(f.id)}
                aria-current={f.id === current.id ? 'true' : undefined}
                className={cn(
                  'flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted/60',
                  f.id === current.id && 'bg-muted',
                )}
              >
                <Badge variant={severityVariant[f.severity]}>{f.severity}</Badge>
                <span className="w-24 shrink-0 font-mono text-xs text-muted-foreground">
                  {f.start == null ? f.source_kind : `${formatTime(f.start)} · ${f.source_kind}`}
                </span>
                <span className="truncate">{f.quote}</span>
                <span className="ml-auto shrink-0 text-xs text-muted-foreground">{f.category}</span>
              </button>
            </li>
          ))}
        </ul>
        <Link to="/findings" className="text-sm text-muted-foreground underline">
          All findings
        </Link>
      </CardContent>
    </Card>
  )
}
