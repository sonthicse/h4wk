import { useQuery } from '@tanstack/react-query'
import { CircleCheckIcon, CircleXIcon, GavelIcon, PlusCircleIcon, RadioTowerIcon } from 'lucide-react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { HoverHighlight, HoverItem } from '@/components/ui/hover-highlight'
import { formatVnDateTime } from '@/lib/format'
import { listEvents, type WatchEvent } from '@/api/watchlist'

const POLL_MS = 5000

// Cùng cách tô màu trạng thái job như trang Collect.
const jobVariant: Record<string, 'secondary' | 'default' | 'outline' | 'destructive'> = {
  queued: 'secondary',
  running: 'default',
  done: 'outline',
  failed: 'destructive',
}

const kindIcon: Record<string, typeof PlusCircleIcon> = {
  channel_added: PlusCircleIcon,
  new_video: RadioTowerIcon,
  job_done: CircleCheckIcon,
  job_failed: CircleXIcon,
  review: GavelIcon,
}

// Dòng chính là thứ người dùng cần nắm: tên video (hoặc tên kênh khi thêm kênh). Dòng phụ nhỏ: kênh và chuyện gì xảy ra.
function mainLine(event: WatchEvent) {
  if (event.kind === 'channel_added') return event.channel_title ?? 'A new channel'
  return event.video_title ?? event.channel_title ?? event.message
}

function whatHappened(event: WatchEvent) {
  switch (event.kind) {
    case 'channel_added':
      return 'now on the watchlist'
    case 'new_video':
      return 'new upload'
    case 'job_done':
      return 'analyzed'
    case 'job_failed':
      return 'collection failed'
    default:
      return event.message
  }
}

function EventItem({ event }: { event: WatchEvent }) {
  const Icon = kindIcon[event.kind] ?? RadioTowerIcon
  const found = event.kind === 'job_done' ? (event.findings ?? null) : null
  const status = event.job?.status
  const failed = event.kind === 'job_failed'
  const title = mainLine(event)
  const sub = [event.kind !== 'channel_added' ? event.channel_title : null, whatHappened(event)].filter(Boolean).join(' · ')
  return (
    <HoverItem className="focus-within:bg-muted">
      <div className="flex gap-3 py-2.5">
        <Icon className={failed ? 'mt-1 size-4 shrink-0 text-destructive' : 'mt-1 size-4 shrink-0 text-muted-foreground'} />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            {event.video_id ? (
              <Link to={`/videos/${event.video_id}`} className="line-clamp-2 text-sm font-medium hover:underline">
                {title}
              </Link>
            ) : (
              <p className="line-clamp-2 text-sm font-medium">{title}</p>
            )}
            {found !== null && found > 0 && (
              <Badge variant="destructive" className="shrink-0">
                {found} {found === 1 ? 'finding' : 'findings'}
              </Badge>
            )}
            {/* Trạng thái job chỉ hiện khi còn đang chạy; xong/lỗi đã thể hiện qua biểu tượng. */}
            {status && status !== 'done' && status !== 'failed' && (
              <Badge variant={jobVariant[status] ?? 'outline'} className="shrink-0">
                {status}
              </Badge>
            )}
          </div>
          <p className="mt-0.5 flex justify-between gap-2 text-xs text-muted-foreground">
            <span className={failed ? 'text-destructive' : undefined}>{sub}</span>
            <time dateTime={event.at} className="shrink-0 tabular-nums">
              {formatVnDateTime(event.at)}
            </time>
          </p>
          {failed && event.error && <p className="mt-1 text-xs text-destructive">{event.error}</p>}
        </div>
      </div>
    </HoverItem>
  )
}

// Dòng sự kiện (T31): poll mỗi 5 giây.
// Cột phải đã tự cuộn nên hiện nhiều hơn.
const MAX_EVENTS = 15

export default function EventFeed() {
  const events = useQuery({
    queryKey: ['events'],
    queryFn: () => listEvents(),
    refetchInterval: POLL_MS,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Events</CardTitle>
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
