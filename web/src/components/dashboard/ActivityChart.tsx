import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import type { DayActivity } from '@/api/dashboard'

const config = {
  captures: { label: 'Captures', color: 'oklch(0.62 0.17 255)' },
  findings: { label: 'Findings', color: 'var(--destructive)' },
} satisfies ChartConfig

// API trả ngày theo giờ Việt Nam dạng YYYY-MM-DD; hiện thành 18/11.
function dayLabel(date: string) {
  const [, m, d] = date.split('-')
  return `${d}/${m}`
}

export default function ActivityChart({ data }: { data: DayActivity[] }) {
  return (
    <Card className="flex h-full min-h-0 flex-col">
      <CardHeader>
        <CardTitle>Activity</CardTitle>
        <CardDescription>Captures and new findings per day, last 14 days</CardDescription>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col">
        <ChartContainer config={config} className="aspect-auto min-h-0 w-full flex-1">
          <BarChart data={data} accessibilityLayer>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="date" tickFormatter={dayLabel} tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={24} />
            <ChartTooltip isAnimationActive={false} content={<ChartTooltipContent labelFormatter={(_, payload) => dayLabel(payload[0]?.payload.date)} />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="captures" fill="var(--color-captures)" radius={3} isAnimationActive={false} />
            <Bar dataKey="findings" fill="var(--color-findings)" radius={3} isAnimationActive={false} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
