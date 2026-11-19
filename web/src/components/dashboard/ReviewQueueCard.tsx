import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { listQueue, type QueueItem } from '@/api/review'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatTime, severityVariant } from '@/lib/findings'

const POLL_MS = 5000
const MAX_ITEMS = 15

// Mở trang Video detail tại đúng nghi vấn, giống danh sách ở trang Review queue.
function reviewLink(item: QueueItem) {
  const f = item.finding
  return `/videos/${encodeURIComponent(f.video_id)}?finding=${encodeURIComponent(f.id)}`
}

function QueueItemRow({ item }: { item: QueueItem }) {
  const f = item.finding
  return (
    <li className="flex gap-3 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <Link to={reviewLink(item)} className="line-clamp-2 text-sm font-medium hover:underline">
            {f.quote}
          </Link>
          <Badge variant={severityVariant[f.severity]} className="shrink-0">
            {f.severity}
          </Badge>
        </div>
        <p className="mt-0.5 flex justify-between gap-2 text-xs text-muted-foreground">
          <span className="truncate">
            {item.video.title ?? item.video.id} · {f.source_kind}
            {f.start != null && ` · ${formatTime(f.start)}`}
          </span>
          <span className="shrink-0">{f.category}</span>
        </p>
      </div>
    </li>
  )
}

// Hàng đợi cần rà soát: chỉ lấy nghi vấn chưa xử lý, poll mỗi 5 giây như dòng sự kiện.
export default function ReviewQueueCard() {
  const queue = useQuery({
    queryKey: ['review-queue', 'dashboard'],
    queryFn: () => listQueue(),
    refetchInterval: POLL_MS,
  })
  const pending = (queue.data ?? []).filter((it) => it.status === 'unreviewed')

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Review</CardTitle>
      </CardHeader>
      <CardContent>
        {queue.error && <p className="text-sm text-destructive">Could not load the review queue.</p>}
        {queue.isPending && <p className="text-sm text-muted-foreground">Loading queue…</p>}
        {queue.data && pending.length === 0 && (
          <p className="text-sm text-muted-foreground">Nothing left to review.</p>
        )}
        {pending.length > 0 && (
          <ol className="divide-y">
            {pending.slice(0, MAX_ITEMS).map((it) => (
              <QueueItemRow key={it.finding.id} item={it} />
            ))}
          </ol>
        )}
        <Link to="/review" className="mt-2 inline-block text-sm text-muted-foreground underline">
          Open review queue
        </Link>
      </CardContent>
    </Card>
  )
}
