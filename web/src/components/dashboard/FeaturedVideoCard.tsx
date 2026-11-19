import { useQuery } from '@tanstack/react-query'
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

// Mô tả YouTube thường mở đầu bằng chính tiêu đề (có khi thêm tên kênh, viết hoa, đổi thứ tự),
// nên bỏ dòng đầu nếu gần như trùng bộ từ với tiêu đề để không bị lặp.
function stripRepeatedTitle(description: string, title?: string | null) {
  if (!title) return description
  const tokens = (s: string) =>
    new Set(
      s
        .normalize('NFD')
        .replace(/\p{Diacritic}/gu, '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, ' ')
        .trim()
        .split(' ')
        .filter(Boolean),
    )
  const titleTokens = tokens(title)
  const lines = description.split(/\r?\n/)
  const first = lines.findIndex((line) => line.trim())
  if (first === -1) return description
  const lineTokens = tokens(lines[first])
  const shared = [...lineTokens].filter((word) => titleTokens.has(word)).length
  const similar = shared / Math.max(lineTokens.size, titleTokens.size)
  return similar >= 0.8 ? lines.slice(first + 1).join('\n').trim() : description
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
  const detail = useQuery({
    queryKey: ['video', topVideoId],
    queryFn: () => getVideo(topVideoId!),
    enabled: topVideoId != null,
  })

  if (!top) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Most serious</CardTitle>
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
  const description = stripRepeatedTitle(detail.data?.video.description ?? '', video?.title)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Most serious</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <EmbeddedPlayer videoId={top.videoId} start={start} />
        <div className="space-y-1">
          <p className="text-lg font-semibold">{video?.title ?? top.videoId}</p>
          {description && (
            <p className="line-clamp-3 text-sm whitespace-pre-line text-muted-foreground">{description}</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
