import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { listQueue, type QueueItem } from '@/api/review'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { HoverHighlight, HoverItem } from '@/components/ui/hover-highlight'
import { formatTime, severityVariant } from '@/lib/findings'

const POLL_MS = 5000
const MAX_ITEMS = 15

// Mở trang Video detail tại đúng nghi vấn, giống danh sách ở trang Review queue.
function reviewLink(item: QueueItem) {
  const f = item.finding
  return `/videos/${encodeURIComponent(f.video_id)}?finding=${encodeURIComponent(f.id)}`
}

// Một dòng như bản phác: mức độ rồi trích dẫn, cắt bớt nếu dài; chi tiết trong tooltip.
function QueueItemRow({ item }: { item: QueueItem }) {
  const f = item.finding
  const detail = `${item.video.title ?? item.video.id} · ${f.source_kind}${f.start != null ? ` · ${formatTime(f.start)}` : ''} · ${f.category}`
  return (
    <HoverItem className="rounded-md focus-within:bg-muted">
      <div className="flex items-center gap-1.5 py-1">
        <Badge variant={severityVariant[f.severity]} className="shrink-0">
          {f.severity}
        </Badge>
        <Link to={reviewLink(item)} title={detail} className="min-w-0 flex-1 truncate hover:underline">
          {f.quote}
        </Link>
      </div>
    </HoverItem>
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
        <CardTitle className="text-lg">Review</CardTitle>
      </CardHeader>
      <CardContent className="max-h-[calc(66svh-9rem)] overflow-y-auto pr-1">
        {queue.error && <p className="text-sm text-destructive">Could not load the review queue.</p>}
        {queue.isPending && <p className="text-sm text-muted-foreground">Loading queue…</p>}
        {queue.data && pending.length === 0 && (
          <p className="text-sm text-muted-foreground">Nothing left to review.</p>
        )}
        {pending.length > 0 && (
          <HoverHighlight>
            <ol>
              {pending.slice(0, MAX_ITEMS).map((it) => (
                <QueueItemRow key={it.finding.id} item={it} />
              ))}
            </ol>
          </HoverHighlight>
        )}
        <Link to="/review" className="mt-2 inline-block text-sm text-muted-foreground underline">
          Open review queue
        </Link>
      </CardContent>
    </Card>
  )
}
