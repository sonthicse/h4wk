import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import type { Finding } from '@/api/findings'
import { listQueue } from '@/api/review'
import { getVideo } from '@/api/videos'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

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
  const detail = useQuery({
    queryKey: ['video', topVideoId],
    queryFn: () => getVideo(topVideoId!),
    enabled: topVideoId != null,
  })

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

  // Phát từ nghi vấn nặng nhất (danh sách đã sắp nặng trước).
  const start = Math.max(0, Math.floor((top.findings[0].start ?? 0) - LEAD_S))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Top video</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <EmbeddedPlayer videoId={top.videoId} start={start} />
        {detail.data?.video.description && (
          <p className="line-clamp-3 text-sm whitespace-pre-line text-muted-foreground">
            {detail.data.video.description}
          </p>
        )}
        <Link to="/findings" className="text-sm text-muted-foreground underline">
          All findings
        </Link>
      </CardContent>
    </Card>
  )
}
