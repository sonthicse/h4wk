import { PlayIcon } from 'lucide-react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatTime, severityVariant } from '@/lib/findings'
import { formatVnDateTime } from '@/lib/format'
import type { FeaturedVideo } from '@/mocks/dashboard'

// Video cần xem trước nhất: nhiều nghi vấn nặng nhất (cách chấm điểm ở mocks/dashboard.ts).
export default function FeaturedVideoCard({ video }: { video: FeaturedVideo | null }) {
  if (!video) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top video</CardTitle>
          <CardDescription>No findings yet. Collect a video to see the one that needs attention first.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const href = `/videos/${video.videoId}?finding=${video.top.id}`
  return (
    <Card>
      <CardHeader>
        <CardDescription>Top video · most serious findings</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-[16rem_minmax(0,1fr)] gap-5">
        {/* Chưa có ảnh thumbnail thật; ô 16:9 giữ chỗ, bấm để mở video tại nghi vấn nặng nhất. */}
        <Link
          to={href}
          aria-label={`Open ${video.title}`}
          className="flex aspect-video items-center justify-center rounded-lg bg-muted text-muted-foreground hover:bg-muted/70"
        >
          <PlayIcon className="size-8" />
        </Link>
        <div className="min-w-0 space-y-3">
          <div>
            <Link to={href} className="line-clamp-2 text-lg font-semibold hover:underline">
              {video.title}
            </Link>
            <p className="text-sm text-muted-foreground">
              {video.channel}
              {video.publishedAt && ` · ${formatVnDateTime(video.publishedAt)}`}
              {video.viewCount !== null && ` · ${video.viewCount.toLocaleString('en-GB')} views`}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {(['high', 'medium', 'low'] as const).map(
              (s) =>
                video.findingsBySeverity[s] > 0 && (
                  <Badge key={s} variant={severityVariant[s]}>
                    {video.findingsBySeverity[s]} {s}
                  </Badge>
                ),
            )}
            <span className="text-muted-foreground">· {video.pending} awaiting review</span>
          </div>
          <blockquote className="border-l-2 pl-3 text-sm italic">
            “{video.top.quote}”
            <span className="ml-2 not-italic text-muted-foreground">
              {video.top.category}
              {video.top.timed && ` · ${formatTime(video.top.start)}`}
            </span>
          </blockquote>
          <Button asChild size="sm">
            <Link to={href}>Open video</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
