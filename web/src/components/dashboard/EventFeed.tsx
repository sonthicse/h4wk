import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { HoverHighlight, HoverItem } from '@/components/ui/hover-highlight'
import { formatVnDateTime } from '@/lib/format'
import { listEvents, type WatchEvent } from '@/api/watchlist'

const POLL_MS = 5000

type BadgeVariant = 'severe' | 'default' | 'destructive' | 'outline' | 'secondary'

// Nhãn và màu theo bản phác: video mới đỏ đặc, xong đen, lỗi đỏ nhạt.
const kindBadge: Record<string, { label: string; variant: BadgeVariant }> = {
  channel_added: { label: 'channel', variant: 'outline' },
  new_video: { label: 'new video', variant: 'severe' },
  job_done: { label: 'done', variant: 'default' },
  job_failed: { label: 'failed', variant: 'destructive' },
  review: { label: 'review', variant: 'outline' },
}

// Một dòng: chuyện gì xảy ra, với video/kênh nào.
function eventText(event: WatchEvent) {
  const video = event.video_title ?? event.video_id
  const channel = event.channel_title
  switch (event.kind) {
    case 'channel_added':
      return `Added ${channel ?? 'a channel'} to the watchlist`
    case 'new_video':
      return `New video detected on ${channel ?? 'a watched channel'}${video ? `: ${video}` : ''}`
    case 'job_done': {
      const n = event.findings ?? 0
      return `Processed video ${video ?? ''}: ${n} ${n === 1 ? 'finding' : 'findings'}`
    }
    case 'job_failed':
      return `Collect failed: ${event.error ?? video ?? event.message}`
    default:
      return event.message
  }
}

function EventItem({ event }: { event: WatchEvent }) {
  const status = event.job?.status
  // Job còn đang chạy thì nhãn là trạng thái job (queued, running).
  const badge =
    status && status !== 'done' && status !== 'failed'
      ? { label: status, variant: 'secondary' as const }
      : (kindBadge[event.kind] ?? { label: event.kind, variant: 'outline' as const })
  const text = eventText(event)
  const at = formatVnDateTime(event.at)
  return (
    <HoverItem className="rounded-md focus-within:bg-muted">
      <div className="flex items-center gap-2 py-1.5">
        <Badge variant={badge.variant} className="shrink-0">
          {badge.label}
        </Badge>
        {event.video_id ? (
          <Link to={`/videos/${event.video_id}`} title={text} className="min-w-0 flex-1 truncate hover:underline">
            {text}
          </Link>
        ) : (
          <span title={text} className="min-w-0 flex-1 truncate">
            {text}
          </span>
        )}
        <time dateTime={event.at} title={at} className="shrink-0 font-mono text-xs text-muted-foreground tabular-nums">
          {at.slice(0, 5)}
        </time>
      </div>
    </HoverItem>
  )
}

// Dòng sự kiện (T31): poll mỗi 5 giây.
// Cột phải đã tự cuộn nên hiện nhiều hơn.
const MAX_EVENTS = 5

export default function EventFeed() {
  const events = useQuery({
    queryKey: ['events'],
    queryFn: () => listEvents(),
    refetchInterval: POLL_MS,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Events</CardTitle>
      </CardHeader>
      <CardContent className="max-h-[calc(66svh-9rem)] overflow-y-auto pr-1">
        {events.error && <p className="text-sm text-destructive">Could not load events.</p>}
        {events.isPending && <p className="text-sm text-muted-foreground">Loading events…</p>}
        {events.data && events.data.length === 0 && (
          <p className="text-sm text-muted-foreground">No events yet. Add a channel to the watchlist or collect a video.</p>
        )}
        {events.data && events.data.length > 0 && (
          <HoverHighlight>
            <ol aria-live="polite" className="divide-y">
              {events.data.slice(0, MAX_EVENTS).map((e) => (
                <EventItem key={e.id} event={e} />
              ))}
            </ol>
          </HoverHighlight>
        )}
      </CardContent>
    </Card>
  )
}
