import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import type { DashboardStats } from '@/mocks/dashboard'

function Meter({ label, note, used, limit, unit }: { label: string; note: string; used: number; limit: number; unit: string }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="font-medium">{label}</span>
        <span className="tabular-nums">
          {used.toLocaleString('en-US')} / {limit.toLocaleString('en-US')} {unit}
        </span>
      </div>
      <Progress value={(used / limit) * 100} aria-label={`${label} used`} />
      <p className="text-xs text-muted-foreground">{note}</p>
    </div>
  )
}

// Quota YouTube Data API và credit Supadata đã dùng (SPEC 10.3).
export default function UsageCard({ youtubeQuota, supadataCredits }: Pick<DashboardStats, 'youtubeQuota' | 'supadataCredits'>) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Source usage</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Meter
          label="YouTube Data API"
          note="Today · resets at midnight Pacific Time (15:00 VN)"
          unit="units"
          {...youtubeQuota}
        />
        <Meter label="Supadata" note="This month" unit="credits" {...supadataCredits} />
      </CardContent>
    </Card>
  )
}
