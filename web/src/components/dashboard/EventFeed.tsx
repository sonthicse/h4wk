import { useQuery } from '@tanstack/react-query'
import { CircleCheckIcon, CircleXIcon, GavelIcon, RadioTowerIcon } from 'lucide-react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatVnDateTime } from '@/lib/format'
import { listEvents, type FeedEvent } from '@/mocks/dashboard'
import { findings } from '@/mocks/data'
import type { JobStatus } from '@/mocks/jobs'

const POLL_MS = 5000

// Chỉ link tới video có trong dữ liệu giả; video watchlist mới chưa có trang chi tiết.
const knownVideos = new Set(findings.map((f) => f.videoId))

// Cùng cách tô màu trạng thái job như trang Collect.
const jobVariant: Record<JobStatus, 'secondary' | 'default' | 'outline' | 'destructive'> = {
  queued: 'secondary',
  running: 'default',
  done: 'outline',
  failed: 'destructive',
}

const kindIcon: Record<FeedEvent['kind'], typeof GavelIcon> = {
  new_video: RadioTowerIcon,
  job_done: CircleCheckIcon,
  job_failed: CircleXIcon,
  review: GavelIcon,
}

function EventItem({ event, caseId }: { event: FeedEvent; caseId: string }) {
  const Icon = kindIcon[event.kind]
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
        {event.videoId && knownVideos.has(event.videoId) && (
          <Link
            to={`/cases/${caseId}/videos/${event.videoId}`}
            className="block truncate text-sm text-muted-foreground hover:text-foreground hover:underline"
          >
            {event.videoTitle}
          </Link>
        )}
        {event.videoId && !knownVideos.has(event.videoId) && (
          <p className="truncate text-sm text-muted-foreground">{event.videoTitle}</p>
        )}
        {event.job && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="font-mono">{event.job.id}</span>
            <Badge variant={jobVariant[event.job.status]}>{event.job.status}</Badge>
          </div>
        )}
        {event.error && <p className="font-mono text-xs [overflow-wrap:anywhere] text-destructive">{event.error}</p>}
      </div>
    </li>
  )
}

// Dòng sự kiện của case (T31): poll mỗi 5 giây.
export default function EventFeed({ caseId }: { caseId: string }) {
  const events = useQuery({
    queryKey: ['events', caseId],
    queryFn: () => listEvents(caseId),
    refetchInterval: POLL_MS,
  })

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Events</CardTitle>
        <CardDescription>Watchlist, jobs and review decisions · refreshes every 5 s</CardDescription>
      </CardHeader>
      <CardContent className="min-h-0 flex-1">
        {events.error && <p className="text-sm text-destructive">Could not load events.</p>}
        {events.isPending && <p className="text-sm text-muted-foreground">Loading events…</p>}
        {events.data && events.data.length === 0 && (
          <p className="text-sm text-muted-foreground">No events yet. Add a channel to the watchlist or collect a video.</p>
        )}
        {events.data && events.data.length > 0 && (
          <div className="h-full overflow-y-auto pr-3">
            <ol aria-live="polite" className="divide-y">
              {events.data.map((e) => (
                <EventItem key={e.id} event={e} caseId={caseId} />
              ))}
            </ol>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
