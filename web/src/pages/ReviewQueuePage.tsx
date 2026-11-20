import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { listVideoQueue, type VideoReviewStatus } from '@/api/review'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { severityVariant, statusVariant } from '@/lib/findings'

// Hàng đợi theo video (T50): mỗi dòng là kết luận của một video; quyết định ghi ở trang video.
type View = VideoReviewStatus | 'all'

const views: { id: View; label: string }[] = [
  { id: 'unreviewed', label: 'Unreviewed' },
  { id: 'needs_info', label: 'Needs info' },
  { id: 'confirmed', label: 'Confirmed' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'all', label: 'All' },
]

export default function ReviewQueuePage() {
  const [view, setView] = useState<View>('unreviewed')
  // Lấy cả danh sách một lần để đếm theo trạng thái; lọc ở client.
  const queue = useQuery({ queryKey: ['review-videos'], queryFn: () => listVideoQueue() })
  const all = queue.data ?? []
  const rows = all.filter((it) => view === 'all' || it.status === view)
  const count = (v: View) => (v === 'all' ? all.length : all.filter((it) => it.status === v).length)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Review queue</h1>
        <Link to="/review/findings" className="text-sm text-primary hover:underline">
          Per-finding view
        </Link>
      </div>
      <div className="flex flex-wrap gap-1">
        {views.map((v) => (
          <Button key={v.id} size="sm" variant={view === v.id ? 'default' : 'ghost'} aria-pressed={view === v.id} onClick={() => setView(v.id)}>
            {v.label} <span className="ml-1 opacity-70">{count(v.id)}</span>
          </Button>
        ))}
      </div>
      <ul className="space-y-2">
        {rows.map((it) => (
          <li key={it.video.id}>
            <Link to={`/videos/${encodeURIComponent(it.video.id)}`} className="block rounded-md border p-3 transition-colors hover:bg-muted">
              <div className="flex flex-wrap items-center gap-2">
                <span className="min-w-0 flex-1 truncate font-medium">{it.video.title ?? it.video.id}</span>
                <Badge variant={it.verdict.violation === 'yes' ? 'destructive' : 'outline'}>{it.verdict.violation}</Badge>
                {it.verdict.severity && <Badge variant={severityVariant[it.verdict.severity]}>{it.verdict.severity}</Badge>}
                <Badge variant={statusVariant[it.status]}>{it.status}</Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {it.video.channel && `${it.video.channel} · `}
                {it.verdict.categories.join(', ') || '—'} · {it.finding_count} findings
              </p>
            </Link>
          </li>
        ))}
        {queue.isPending && <li className="p-6 text-center text-sm text-muted-foreground">Loading…</li>}
        {queue.error && <li className="p-6 text-center text-sm text-destructive">Could not load the queue: {queue.error.message}</li>}
        {queue.data && rows.length === 0 && <li className="p-6 text-center text-sm text-muted-foreground">Nothing to review here.</li>}
      </ul>
    </div>
  )
}
