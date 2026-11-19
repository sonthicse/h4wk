import { useQuery } from '@tanstack/react-query'
import { CircleCheckIcon, CircleXIcon, PlusCircleIcon, RadioTowerIcon } from 'lucide-react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatVnDateTime } from '@/lib/format'
import { listVideos } from '@/api/videos'
import { listEvents, listWatchItems, type WatchEvent } from '@/api/watchlist'

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

type Names = { video: (id: string) => string | null; channel: (watchItem: string | null | undefined) => string | null }

// Backend ghi "…: N findings" trong message của job_done; tách số ra để hiện badge.
function findingCount(message: string) {
  const m = message.match(/(\d+) findings?/)
  return m ? Number(m[1]) : null
}

// Câu ngắn dễ đọc theo loại sự kiện; tên video/kênh lấy từ danh sách video và watchlist, không hiện mã.
function headline(event: WatchEvent, names: Names) {
  const channel = names.channel(event.watch_item)
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

function EventItem({ event, names }: { event: WatchEvent; names: Names }) {
  const Icon = kindIcon[event.kind] ?? RadioTowerIcon
  const title = event.video_id ? (names.video(event.video_id) ?? 'Untitled video (still collecting)') : null
  const found = event.kind === 'job_done' ? findingCount(event.message) : null
  const status = event.job?.status
  return (
    <li className="flex gap-3 py-3">
      <Icon className={event.kind === 'job_failed' ? 'mt-0.5 size-4 shrink-0 text-destructive' : 'mt-0.5 size-4 shrink-0 text-muted-foreground'} />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium">{headline(event, names)}</p>
          <time dateTime={event.at} className="shrink-0 text-xs text-muted-foreground tabular-nums">
            {formatVnDateTime(event.at)}
          </time>
        </div>
        {event.video_id && title && (
          <Link to={`/videos/${event.video_id}`} className="block truncate text-sm text-muted-foreground hover:text-foreground hover:underline">
            {title}
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
        {event.kind === 'job_failed' && <p className="text-xs text-destructive">{event.message}</p>}
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
  const videos = useQuery({ queryKey: ['videos'], queryFn: listVideos, refetchInterval: POLL_MS })
  const watchlist = useQuery({ queryKey: ['watchlist'], queryFn: listWatchItems })
  const names: Names = {
    video: (id) => videos.data?.find((v) => v.id === id)?.title ?? null,
    channel: (w) => (w ? (watchlist.data?.find((i) => i.id === w)?.title ?? null) : null),
  }

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
              <EventItem key={e.id} event={e} names={names} />
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  )
}
