import { useQuery } from '@tanstack/react-query'
import { ExternalLink } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import CapturesTab from '@/components/video/CapturesTab'
import CommentsTab from '@/components/video/CommentsTab'
import FindingTimeline from '@/components/video/FindingTimeline'
import KeyframeStrip from '@/components/video/KeyframeStrip'
import Player from '@/components/video/Player'
import TranscriptPane from '@/components/video/TranscriptPane'
import { usePlayer } from '@/components/video/usePlayer'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatVnDateTime } from '@/lib/format'
import { timedSources } from '@/lib/findings'
import { findings as allFindings, type Finding } from '@/mocks/data'
import { getVideo, type VideoDetail } from '@/mocks/videos'

// Nhảy tới start − 2s, không âm (SPEC 8, màn 1).
const LEAD_S = 2

type Tab = 'comments' | 'captures'

function VideoView({ video, findings, finding, t }: { video: VideoDetail; findings: Finding[]; finding: Finding | null; t: number | null }) {
  const [, setSearchParams] = useSearchParams()
  const startAt = finding && timedSources.has(finding.sourceKind) ? finding.start - LEAD_S : t
  const hasTarget = startAt !== null
  const player = usePlayer(video.durationS, Math.min(Math.max(startAt ?? 0, 0), video.durationS), hasTarget)
  const [tab, setTab] = useState<Tab>('comments')

  const ownHref = `/cases/${video.caseId}/videos/${video.id}`
  const findingHref = (id: string) => `${ownHref}?finding=${id}`

  // Bấm một nghi vấn: đổi ?finding=, trang dựng lại trình phát (xem key bên dưới) và nhảy tới đúng chỗ.
  const openFinding = (f: Finding) => setSearchParams({ finding: f.id })

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">{video.title}</h1>
          <p className="text-sm text-muted-foreground">
            {video.channel} · published {formatVnDateTime(video.publishedAt)}
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-2 text-sm">
          <Badge variant="outline">{video.viewCount.toLocaleString('en-GB')} views</Badge>
          <Badge variant="outline">{video.likeCount.toLocaleString('en-GB')} likes</Badge>
          <Badge variant="outline">{video.commentCount.toLocaleString('en-GB')} comments</Badge>
          <Badge variant={findings.length > 0 ? 'destructive' : 'outline'}>{findings.length} findings</Badge>
          <a
            href={`https://www.youtube.com/watch?v=${video.id}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-primary hover:underline"
          >
            Open on YouTube <ExternalLink className="size-3.5" />
          </a>
        </div>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_24rem] items-start gap-6">
        <div className="min-w-0 space-y-6">
          <div className="max-w-3xl"><Player player={player} activeFinding={finding} /></div>
          <FindingTimeline findings={findings} player={player} activeId={finding?.id ?? null} onOpen={openFinding} />
          <KeyframeStrip keyframes={video.keyframes} findings={findings} player={player} activeFinding={finding} />
          <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)}>
            <TabsList>
              <TabsTrigger value="comments">Comments ({video.comments.length})</TabsTrigger>
              <TabsTrigger value="captures">Captures ({video.captures.length})</TabsTrigger>
            </TabsList>
            <TabsContent value="comments">
              <CommentsTab comments={video.comments} highlightId={finding?.id ?? null} findingHref={findingHref} />
            </TabsContent>
            <TabsContent value="captures">
              <CapturesTab captures={video.captures} caseId={video.caseId} videoId={video.id} />
            </TabsContent>
          </Tabs>
        </div>
        <div className="sticky top-4 h-[calc(100vh-7rem)]">
          <TranscriptPane transcripts={video.transcripts} findings={findings} player={player} activeId={finding?.id ?? null} />
        </div>
      </div>
    </div>
  )
}

export default function VideoDetailPage() {
  const { caseId = '', videoId = '' } = useParams()
  const [params] = useSearchParams()
  const video = useQuery({ queryKey: ['video', caseId, videoId], queryFn: () => getVideo(caseId, videoId) })

  if (video.isPending) return <Skeleton className="h-96 w-full" />
  if (video.error) return <p className="text-sm text-destructive">Could not load this video.</p>
  if (!video.data) {
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Video not found</h1>
        <p className="text-sm text-muted-foreground">
          No video <span className="font-mono">{videoId}</span> in this case.{' '}
          <Link to={`/cases/${caseId}/findings`} className="underline">Back to findings</Link>
        </p>
      </div>
    )
  }

  const findings = allFindings.filter((f) => f.caseId === caseId && f.videoId === videoId)
  const finding = findings.find((f) => f.id === params.get('finding')) ?? null
  const tParam = Number(params.get('t'))
  const t = params.get('t') !== null && Number.isFinite(tParam) ? tParam : null

  // key: đổi ?t= hoặc ?finding= thì dựng lại trình phát để nó nhảy tới vị trí mới.
  return <VideoView key={`${videoId}:${t}:${finding?.id}`} video={video.data} findings={findings} finding={finding} t={t} />
}
