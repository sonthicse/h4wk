import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import type { DashboardStats, Usage } from '@/api/dashboard'

const num = (n: number) => n.toLocaleString('en-US')

// usage = null: nguồn chưa theo dõi mức dùng (T14/T15 chưa làm).
// period: "today" (YouTube, reset theo ngày) hoặc "this month" (Supadata).
function Meter({ label, period, usage, unit }: { label: string; period: string; usage: Usage | null | undefined; unit: string }) {
  if (!usage) {
    return (
      <div className="flex items-baseline justify-between gap-2 text-[13px]">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">Not tracked yet</span>
      </div>
    )
  }
  const { used, limit } = usage
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between gap-2 text-[13px]">
        <span className="font-medium">{label}</span>
        <span className="text-right tabular-nums text-muted-foreground">
          {num(used)} / {num(limit)} {unit} {period} · {num(Math.max(limit - used, 0))} left
        </span>
      </div>
      <Progress value={(used / limit) * 100} aria-label={`${label} used`} />
    </div>
  )
}

// Quota YouTube Data API, credit Supadata và token Jev đã dùng.
export default function UsageCard({ youtubeQuota, supadataCredits, jevUsage }: { youtubeQuota: Usage | null | undefined; supadataCredits: Usage | null | undefined; jevUsage: DashboardStats['jev_usage'] }) {
  return (
    <Card className="self-start">
      <CardHeader>
        <CardTitle>Usage</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2.5">
        <Meter label="YouTube Data API" period="today" unit="units" usage={youtubeQuota} />
        <Meter label="Supadata" period="this month" unit="credits" usage={supadataCredits} />
        <div className="space-y-1 text-[13px]">
          <div className="flex flex-wrap items-baseline justify-between gap-x-2">
            <span className="font-medium">Jev</span>
            <span className="text-muted-foreground">This month (VN)</span>
          </div>
          {/* Chưa có request hoặc TypeSafe không báo số thì hiện 0. */}
          <p className="tabular-nums">
            Requests: {num(jevUsage?.requests ?? 0)} · Input: {num(jevUsage?.input_tokens ?? 0)} · Output: {num(jevUsage?.output_tokens ?? 0)}
          </p>
          <p className="text-xs text-muted-foreground">Token counts reported by TypeSafe. Totals include only reported counts.</p>
        </div>
      </CardContent>
    </Card>
  )
}
