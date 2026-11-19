import { useQuery } from '@tanstack/react-query'
import { CircleCheckIcon, CircleXIcon, GavelIcon, PlusCircleIcon, RadioTowerIcon } from 'lucide-react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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

// Câu ngắn dễ đọc theo loại sự kiện; tên kênh/video lấy thẳng từ sự kiện, không hiện mã.
function headline(event: WatchEvent) {
  const channel = event.channel_title
  switch (event.kind) {
    case 'channel_added':
      return channel ? `Started watching ${channel}` : 'Started watching a channel'
    case 'new_video':
      return channel ? `New video on ${channel}` : 'New video detected'
    case 'job_done':
      return 'Video analyzed'
    case 'job_failed':
      return 'Collection failed'
    default:
      return event.message
  }
}

function EventItem({ event }: { event: WatchEvent }) {
  const Icon = kindIcon[event.kind] ?? RadioTowerIcon
  const found = event.kind === 'job_done' ? (event.findings ?? null) : null
  const status = event.job?.status
  return (
    <li className="flex gap-3 py-3">
      <Icon className={event.kind === 'job_failed' ? 'mt-0.5 size-4 shrink-0 text-destructive' : 'mt-0.5 size-4 shrink-0 text-muted-foreground'} />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium">{headline(event)}</p>
          <time dateTime={event.at} className="shrink-0 text-xs text-muted-foreground tabular-nums">
            {formatVnDateTime(event.at)}
          </time>
        </div>
        {event.video_id && (
          <Link to={`/videos/${event.video_id}`} className="block truncate text-sm text-muted-foreground hover:text-foreground hover:underline">
            {event.video_title ?? 'Untitled video (still collecting)'}
          </Link>
        )}
        <div className="flex items-center gap-2">
          {found !== null && (
            <Badge variant={found > 0 ? 'destructive' : 'outline'}>
              {found === 0 ? 'No findings' : `${found} ${found === 1 ? 'finding' : 'findings'}`}
            </Badge>
          )}
          {/* Chỉ hiện trạng thái job khi còn đang chạy; xong/lỗi đã thể hiện qua biểu tượng. */}
          {status && status !== 'done' && status !== 'failed' && <Badge variant={jobVariant[status] ?? 'outline'}>{status}</Badge>}
        </div>
        {event.kind === 'job_failed' && event.error && <p className="text-xs text-destructive">{event.error}</p>}
      </div>
    </li>
  )
}

// Dòng sự kiện (T31): poll mỗi 5 giây.
// Chỉ hiện vài sự kiện mới nhất cho vừa một màn hình, không cuộn.
const MAX_EVENTS = 6

export default function EventFeed() {
  const events = useQuery({
    queryKey: ['events'],
    queryFn: () => listEvents(),
    refetchInterval: POLL_MS,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Events</CardTitle>
        <CardDescription>Watchlist, jobs and review decisions · refreshes every 5 s</CardDescription>
      </CardHeader>
      <CardContent>
        {events.error && <p className="text-sm text-destructive">Could not load events.</p>}
        {events.isPending && <p className="text-sm text-muted-foreground">Loading events…</p>}
        {events.data && events.data.length === 0 && (
          <p className="text-sm text-muted-foreground">No events yet. Add a channel to the watchlist or collect a video.</p>
        )}
        {events.data && events.data.length > 0 && (
          <ol aria-live="polite" className="divide-y">
            {events.data.slice(0, MAX_EVENTS).map((e) => (
              <EventItem key={e.id} event={e} />
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  )
}
