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
import type { DayActivity } from '@/mocks/dashboard'

const config = {
  captures: { label: 'Captures', color: 'var(--chart-2)' },
  findings: { label: 'Findings', color: 'var(--chart-4)' },
} satisfies ChartConfig

// Ngày hiện theo giờ Việt Nam, dạng 18/11.
function dayLabel(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit' })
}

export default function ActivityChart({ data }: { data: DayActivity[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity</CardTitle>
        <CardDescription>Captures and new findings per day, last 14 days</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config} className="aspect-auto h-56 w-full">
          <BarChart data={data} accessibilityLayer>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="date" tickFormatter={dayLabel} tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={24} />
            <ChartTooltip content={<ChartTooltipContent labelFormatter={(_, payload) => dayLabel(payload[0]?.payload.date)} />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="captures" fill="var(--color-captures)" radius={3} isAnimationActive={false} />
            <Bar dataKey="findings" fill="var(--color-findings)" radius={3} isAnimationActive={false} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
