import { CountingNumber } from '@animate-ui/react/primitives/texts/counting-number'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import ActivityChart from '@/components/dashboard/ActivityChart'
import Donut from '@/components/dashboard/Donut'
import EventFeed from '@/components/dashboard/EventFeed'
import FeaturedVideoCard from '@/components/dashboard/FeaturedVideoCard'
import ReviewQueueCard from '@/components/dashboard/ReviewQueueCard'
import UsageCard from '@/components/dashboard/UsageCard'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { severityVariant } from '@/lib/findings'
import { getDashboard } from '@/api/dashboard'
import type { Finding } from '@/api/findings'
import type { ReviewStatus } from '@/api/review'

const severities: Finding['severity'][] = ['high', 'medium', 'low']
const statuses: ReviewStatus[] = ['unreviewed', 'confirmed', 'rejected', 'needs_info']

const cardLink =
  'block rounded-xl transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none [&>*]:hover:bg-muted/40'

function StatCard({ label, value, to }: { label: string; value: number; to: string }) {
  return (
    <Link to={to} aria-label={`${label}: ${value}`} className={cardLink}>
      <Card className="h-full">
        <CardHeader>
          <CardDescription>{label}</CardDescription>
          <CardTitle className="text-3xl tabular-nums">
            <CountingNumber number={value} />
          </CardTitle>
        </CardHeader>
      </Card>
    </Link>
  )
}

const sliceColor: Record<string, string> = {
  high: '#dc2626',
  medium: '#f59e0b',
  low: '#d4d4d4',
  unreviewed: '#f59e0b',
  confirmed: '#dc2626',
  rejected: '#737373',
  needs_info: '#3b82f6',
}

type BadgeVariant = 'severe' | 'warning' | 'outline' | 'info' | 'neutral'

const reviewVariant: Record<ReviewStatus, BadgeVariant> = {
  unreviewed: 'warning',
  confirmed: 'severe',
  rejected: 'neutral',
  needs_info: 'info',
}

function Breakdown<K extends string>({
  title,
  to,
  keys,
  counts,
  variant,
  centerLabel,
}: {
  title: string
  to: string
  keys: K[]
  counts: Record<K, number>
  variant: Record<K, BadgeVariant>
  centerLabel: string
}) {
  return (
    <Link
      to={to}
      aria-label={`${title}: open the ${title.toLowerCase()} page`}
      className={cardLink}
    >
      <Card className="h-full">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          <Donut
            centerLabel={centerLabel}
            slices={keys.map((k) => ({ key: k, label: k, value: counts[k] ?? 0, color: sliceColor[k] ?? 'var(--muted-foreground)' }))}
          />
          <ul className="min-w-0 flex-1 space-y-1.5">
            {keys.map((k) => (
              <li key={k} className="flex items-center justify-between gap-2">
                <Badge variant={variant[k]}>{k}</Badge>
                <span className="tabular-nums">{counts[k] ?? 0}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </Link>
  )
}

export default function DashboardPage() {

  const stats = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard, refetchInterval: 5000 })

  if (stats.isPending) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (stats.error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load the dashboard</AlertTitle>
        <AlertDescription>Try reloading the page.</AlertDescription>
      </Alert>
    )
  }

  const d = stats.data

  return (
    <div className="flex h-[calc(100svh-6rem)] flex-col gap-4">
      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,9fr)_minmax(0,11fr)] gap-4">
        <div className="-m-1 flex min-h-0 flex-col gap-4 p-1">
          <div className="grid shrink-0 grid-cols-[minmax(0,2fr)_minmax(0,1fr)] items-start gap-4">
            <FeaturedVideoCard topVideoId={d.top_video?.id ?? null} />
            <div className="flex flex-col gap-4">
              <StatCard label="Watched channels" value={d.channel_count} to="/watchlist" />
              <StatCard label="Videos collected" value={d.video_count} to="/videos" />
              <StatCard label="Captures" value={d.capture_count} to="/collect" />
            </div>
          </div>
          <div className="min-h-0 flex-1">
            <ActivityChart data={d.activity} />
          </div>
        </div>
        <div className="-m-1 min-h-0 overflow-y-auto p-1 pr-2">
          <div className="grid grid-cols-2 gap-4">
            <Breakdown title="Findings" to="/findings" centerLabel="findings" keys={severities} counts={d.findings_by_severity} variant={severityVariant} />
            <Breakdown title="Review" to="/review" centerLabel={d.videos_by_review_status ? 'videos' : 'findings'} keys={statuses} counts={d.videos_by_review_status ?? d.findings_by_status} variant={reviewVariant} />
            <div className="col-span-2">
              <ReviewQueueCard />
            </div>
            <EventFeed />
            <UsageCard youtubeQuota={d.youtube_quota} supadataCredits={d.supadata_credits} jevUsage={d.jev_usage} />
          </div>
        </div>
      </div>
    </div>
  )
}
