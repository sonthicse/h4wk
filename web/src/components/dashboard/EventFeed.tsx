import { useQuery } from '@tanstack/react-query'
import { CircleCheckIcon, CircleXIcon, PlusCircleIcon, RadioTowerIcon } from 'lucide-react'
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
}

function EventItem({ event }: { event: WatchEvent }) {
  const Icon = kindIcon[event.kind] ?? RadioTowerIcon
  return (
    <li className="flex gap-3 py-3">
      <Icon className={event.kind === 'job_failed' ? 'mt-0.5 size-4 shrink-0 text-destructive' : 'mt-0.5 size-4 shrink-0 text-muted-foreground'} />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium">{event.message}</p>
          <time dateTime={event.at} className="shrink-0 text-xs text-muted-foreground tabular-nums">
            {formatVnDateTime(event.at)}
          </time>
        </div>
        {event.video_id && (
          <Link
            to={`/videos/${event.video_id}`}
            className="block truncate font-mono text-xs text-muted-foreground hover:text-foreground hover:underline"
          >
            {event.video_id}
          </Link>
        )}
        {event.job && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="font-mono">{event.job.id}</span>
            <Badge variant={jobVariant[event.job.status] ?? 'outline'}>{event.job.status}</Badge>
          </div>
        )}
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
        <CardDescription>Watchlist and collection jobs · refreshes every 5 s</CardDescription>
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
