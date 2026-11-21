import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import type { DashboardStats, Usage } from '@/api/dashboard'

// usage = null: nguồn chưa theo dõi mức dùng (T14/T15 chưa làm).
function Meter({ label, note, usage, unit }: { label: string; note: string; usage: Usage | null | undefined; unit: string }) {
  if (!usage) {
    return (
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">Not tracked yet</span>
      </div>
    )
  }
  const { used, limit } = usage
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="font-medium">{label}</span>
        <span className="tabular-nums text-muted-foreground">
          {used.toLocaleString('en-US')} / {limit.toLocaleString('en-US')} {unit} · {Math.max(limit - used, 0).toLocaleString('en-US')} left
        </span>
      </div>
      <Progress value={(used / limit) * 100} aria-label={`${label} used`} />
      <p className="text-xs text-muted-foreground">{note}</p>
    </div>
  )
}

// Quota YouTube Data API và credit Supadata đã dùng (SPEC 10.3).
export default function UsageCard({ youtubeQuota, supadataCredits, jevUsage }: { youtubeQuota: Usage | null | undefined; supadataCredits: Usage | null | undefined; jevUsage: DashboardStats['jev_usage'] }) {
  return (
    <Card className="self-start">
      <CardHeader>
        <CardTitle>Source usage</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Meter
          label="YouTube Data API"
          note="Today · resets at midnight Pacific Time (15:00 VN)"
          unit="units"
          usage={youtubeQuota}
        />
        <Meter label="Supadata" note="This month" unit="credits" usage={supadataCredits} />
        <div className="space-y-1.5 text-sm">
          <div className="flex flex-wrap items-baseline justify-between gap-x-2">
            <span className="font-medium">Jev</span>
            <span className="text-muted-foreground">This month (VN)</span>
          </div>
          {jevUsage ? (
            <p className="tabular-nums">
              Requests: {jevUsage.requests.toLocaleString('en-US')} · Input: {jevUsage.input_tokens?.toLocaleString('en-US') ?? 'Not reported'} · Output: {jevUsage.output_tokens?.toLocaleString('en-US') ?? 'Not reported'}
            </p>
          ) : <p className="text-muted-foreground">No requests this month</p>}
          <p className="text-xs text-muted-foreground">Token counts reported by TypeSafe. Totals include only reported counts.</p>
        </div>
      </CardContent>
    </Card>
  )
}
