import { useQuery } from '@tanstack/react-query'
import ActivityChart from '@/components/dashboard/ActivityChart'
import EventFeed from '@/components/dashboard/EventFeed'
import FeaturedVideoCard from '@/components/dashboard/FeaturedVideoCard'
import UsageCard from '@/components/dashboard/UsageCard'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { severityVariant, statusVariant } from '@/lib/findings'
import { getDashboard } from '@/mocks/dashboard'
import type { ReviewStatus, Severity } from '@/mocks/data'

const severities: Severity[] = ['high', 'medium', 'low']
const statuses: ReviewStatus[] = ['pending', 'confirmed', 'rejected', 'needs_info']

// Một con số kèm dòng giải thích ngắn nó đếm cái gì.
function StatCard({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-3xl tabular-nums">{value}</CardTitle>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </CardHeader>
    </Card>
  )
}

function Breakdown<K extends string>({
  title,
  keys,
  counts,
  variant,
}: {
  title: string
  keys: K[]
  counts: Record<K, number>
  variant: Record<K, 'destructive' | 'default' | 'secondary' | 'outline'>
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {keys.map((k) => (
            <li key={k} className="flex items-center justify-between">
              <Badge variant={variant[k]}>{k}</Badge>
              <span className="text-lg font-medium tabular-nums">{counts[k]}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  // Số liệu cũng làm mới mỗi 5 giây để khớp với dòng sự kiện (video watchlist xử lý xong thì số tăng).
  const stats = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard, refetchInterval: 5000 })

  if (stats.isPending) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
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
  const totalFindings = severities.reduce((sum, s) => sum + d.findingsBySeverity[s], 0)

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <div className="flex gap-2 text-sm">
          <Badge variant="outline">{totalFindings} {totalFindings === 1 ? 'finding' : 'findings'}</Badge>
        </div>
      </div>

      <div className="grid grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-4">
        <div className="space-y-4">
          <FeaturedVideoCard video={d.featured} />
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Watched channels" value={d.channelCount} hint="Channels in the watchlist" />
            <StatCard label="Videos collected" value={d.videoCount} hint="Different videos saved so far" />
            <StatCard label="Captures" value={d.captureCount} hint="Collection runs; one video can be collected again" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Breakdown title="Findings by severity" keys={severities} counts={d.findingsBySeverity} variant={severityVariant} />
            <Breakdown title="Findings by review status" keys={statuses} counts={d.findingsByStatus} variant={statusVariant} />
          </div>
          <ActivityChart data={d.activity} />
          <UsageCard youtubeQuota={d.youtubeQuota} supadataCredits={d.supadataCredits} />
        </div>
        <EventFeed />
      </div>
    </div>
  )
}
