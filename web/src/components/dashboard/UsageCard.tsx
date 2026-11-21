import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import type { Usage } from '@/api/dashboard'

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
export default function UsageCard({ youtubeQuota, supadataCredits }: { youtubeQuota: Usage | null | undefined; supadataCredits: Usage | null | undefined }) {
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
          usage={youtubeQuota}
        />
        <Meter label="Supadata" note="This month" unit="credits" usage={supadataCredits} />
      </CardContent>
    </Card>
  )
}
