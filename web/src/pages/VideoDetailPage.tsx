import { useQuery } from '@tanstack/react-query'
import { ExternalLink } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { listEntities } from '@/api/entities'
import { listQueue, type QueueItem } from '@/api/review'
import {
  getTimeline,
  getVideo,
  listComments,
  listTranscripts,
  mediaUrl,
  toVideoFinding,
  type VideoDetail,
  type VideoFinding,
} from '@/api/videos'
import CapturesTab from '@/components/video/CapturesTab'
import CommentsTab from '@/components/video/CommentsTab'
import FindingTimeline from '@/components/video/FindingTimeline'
import KeyframeStrip from '@/components/video/KeyframeStrip'
import { buildKeyframes } from '@/components/video/keyframes'
import EvidencePanel from '@/components/video/EvidencePanel'
import VerdictCard from '@/components/video/VerdictCard'
import Player from '@/components/video/Player'
import TranscriptPane from '@/components/video/TranscriptPane'
import { usePlayer } from '@/components/video/usePlayer'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatVnDateTime } from '@/lib/format'
import { timedSources } from '@/lib/findings'

// Nhảy tới start − 2s, không âm (SPEC 8, màn 1).
const LEAD_S = 2

type Tab = 'comments' | 'captures'

const count = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('en-GB'))

function VideoView({
  detail,
  findings,
  items,
  finding,
  t,
}: {
  detail: VideoDetail
  items: QueueItem[]
  findings: VideoFinding[]
  finding: VideoFinding | null
  t: number | null
}) {
  const { video, channel, captures } = detail
  const [, setSearchParams] = useSearchParams()
  const [tab, setTab] = useState<Tab>('comments')

  // Không truyền ?capture=: backend tự lấy bản thu mới nhất có loại dữ liệu đó. has_media cho biết có file video không.
  const hasMedia = captures.some((c) => c.has_media)

  const timeline = useQuery({ queryKey: ['timeline', video.id], queryFn: () => getTimeline(video.id) })
  const transcripts = useQuery({
    queryKey: ['transcripts', video.id],
    queryFn: () => listTranscripts(video.id),
  })
  const comments = useQuery({
    queryKey: ['comments', video.id],
    queryFn: () => listComments(video.id),
  })
  const entities = useQuery({ queryKey: ['entities'], queryFn: listEntities })

  const entityNames = useMemo(() => Object.fromEntries((entities.data ?? []).map((e) => [e.id, e.name])), [entities.data])
  const keyframes = useMemo(() => buildKeyframes(timeline.data, findings, entityNames), [timeline.data, findings, entityNames])
  const findingByComment = useMemo(
    () => new Map(findings.flatMap((f) => (f.commentId ? [[f.commentId, f.id] as const] : []))),
    [findings],
  )
  const commentList = comments.data ?? []

  // Độ dài lấy từ metadata; thiếu thì suy từ timeline/nghi vấn để thanh thời gian vẫn vẽ được.
  const durationHint =
    video.duration_s ??
    Math.max(0, ...(timeline.data?.segments ?? []).map((s) => s.end), ...findings.map((f) => f.end ?? 0))

  // ?t= (bấm một đoạn cụ thể của nghi vấn nhiều chỗ) được ưu tiên hơn start của nghi vấn.
  const startAt = t ?? (finding && timedSources.has(finding.sourceKind) && finding.start !== null ? finding.start - LEAD_S : null)
  const hasTarget = startAt !== null
  const { controls: player, videoProps, failed } = usePlayer(durationHint, Math.max(startAt ?? 0, 0), hasTarget)

  const ownHref = `/videos/${video.id}`
  const findingHref = (id: string) => `${ownHref}?finding=${id}`

  // Bấm một nghi vấn: đổi ?finding=, trang dựng lại trình phát (xem key bên dưới) và nhảy tới đúng chỗ.
  const openFinding = (f: VideoFinding, at?: number) =>
    setSearchParams(at === undefined ? { finding: f.id } : { finding: f.id, t: String(Math.max(0, at - LEAD_S)) })

  // Bấm bằng chứng: comment thì mở tab Comments và đánh dấu nghi vấn; còn lại tua tới start như openFinding.
  const openEvidence = (it: QueueItem) => {
    const vf = toVideoFinding(it)
    if (vf.sourceKind === 'comment') setTab('comments')
    openFinding(vf, timedSources.has(vf.sourceKind) && vf.start !== null ? vf.start : undefined)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col items-start justify-between gap-4 md:flex-row">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">{video.title}</h1>
          <p className="text-sm text-muted-foreground">
            {channel?.title ?? video.channel_id}
            {video.published_at && <> · published {formatVnDateTime(video.published_at)}</>}
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-2 text-sm">
          {/* YouTube có thể ẩn số liệu (null): khi đó bỏ hẳn badge thay vì hiện "—". */}
          {video.view_count != null && <Badge variant="outline">{count(video.view_count)} views</Badge>}
          {video.like_count != null && <Badge variant="outline">{count(video.like_count)} likes</Badge>}
          {video.comment_count != null && <Badge variant="outline">{count(video.comment_count)} comments</Badge>}
          <Badge variant={findings.length > 0 ? 'destructive' : 'outline'}>{findings.length} findings</Badge>
          <a
            href={`https://www.youtube.com/watch?v=${encodeURIComponent(video.id)}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-primary hover:underline"
          >
            YouTube <ExternalLink className="size-3.5" />
          </a>
        </div>
      </div>

      <VerdictCard videoId={video.id} />

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_24rem] items-start gap-6">
        <div className="min-w-0 space-y-6">
          <div className="max-w-3xl">
            <Player
              player={player}
              videoProps={videoProps}
              src={hasMedia ? mediaUrl(video.id) : null}
              failed={failed}
              activeFinding={finding}
              videoId={video.id}
              capture={timeline.data?.capture}
              keyframes={keyframes}
              findings={findings}
            />
          </div>
          <FindingTimeline findings={findings} player={player} activeId={finding?.id ?? null} onOpen={openFinding}>
            <KeyframeStrip
              videoId={video.id}
              capture={timeline.data?.capture}
              keyframes={keyframes}
              findings={findings}
              player={player}
            />
          </FindingTimeline>
          <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)}>
            <TabsList>
              <TabsTrigger value="comments">Comments ({commentList.length})</TabsTrigger>
              <TabsTrigger value="captures">Captures ({captures.length})</TabsTrigger>
            </TabsList>
            <TabsContent value="comments">
              {comments.isPending ? (
                <Skeleton className="mt-2 h-24 w-full" />
              ) : comments.error ? (
                <p className="py-4 text-sm text-destructive">Could not load comments.</p>
              ) : (
                <CommentsTab
                  comments={commentList}
                  findingByComment={findingByComment}
                  highlightId={finding?.id ?? null}
                  findingHref={findingHref}
                />
              )}
            </TabsContent>
            <TabsContent value="captures">
              <CapturesTab captures={[...captures].reverse()} videoId={video.id} />
            </TabsContent>
          </Tabs>
        </div>
        <div className="space-y-4 lg:sticky lg:top-4">
          <div className="h-96 lg:h-[calc(100vh-14rem)] lg:min-h-80">
            <TranscriptPane
              transcripts={transcripts.data ?? []}
              findings={findings}
              player={player}
              activeId={finding?.id ?? null}
              primaryKind={timeline.data?.transcript_kind ?? null}
            />
          </div>
          <EvidencePanel videoId={video.id} items={items} onOpen={openEvidence} />
        </div>
      </div>
    </div>
  )
}

export default function VideoDetailPage() {
  const { videoId = '' } = useParams()
  const [params] = useSearchParams()
  const video = useQuery({ queryKey: ['video', videoId], queryFn: () => getVideo(videoId) })
  const queue = useQuery({
    queryKey: ['queue', 'video', videoId],
    queryFn: () => listQueue({ video: videoId, latestOnly: false }),
    enabled: video.data != null,
  })

  if (video.isPending) return <Skeleton className="h-96 w-full" />
  if (video.error) return <p className="text-sm text-destructive">Could not load this video.</p>
  if (!video.data) {
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Video not found</h1>
        <p className="text-sm text-muted-foreground">
          No video <span className="font-mono">{videoId}</span>.{' '}
          <Link to="/findings" className="underline">Back to findings</Link>
        </p>
      </div>
    )
  }
  if (queue.isPending) return <Skeleton className="h-96 w-full" />
  if (queue.error) return <p className="text-sm text-destructive">Could not load findings for this video.</p>

  // Hàng đợi gồm nghi vấn của mọi bản thu; chỉ hiện bản thu của nghi vấn đang mở, không có thì bản thu mới nhất có nghi vấn.
  const all = queue.data.map(toVideoFinding)
  const active = all.find((f) => f.id === params.get('finding')) ?? null
  const capture = active?.capture ?? all.reduce((max, f) => (f.capture > max ? f.capture : max), '')
  const findings = all.filter((f) => f.capture === capture)
  const items = queue.data.filter((it) => it.finding.capture === capture)
  const finding = active
  const tParam = Number(params.get('t'))
  const t = params.get('t') !== null && Number.isFinite(tParam) ? tParam : null

  // key: đổi ?t= hoặc ?finding= thì dựng lại trình phát để nó nhảy tới vị trí mới.
  return <VideoView key={`${videoId}:${t}:${finding?.id}`} detail={video.data} findings={findings} items={items} finding={finding} t={t} />
}
