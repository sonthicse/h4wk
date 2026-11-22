import { Cell, Pie, PieChart } from 'recharts'
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart'

export type DonutSlice = { key: string; label: string; value: number; color: string }

// Biểu đồ vòng tròn: mỗi nhóm một cung, tổng số ở giữa. Không có dữ liệu thì vẽ vòng xám.
export default function Donut({ slices, centerLabel }: { slices: DonutSlice[]; centerLabel: string }) {
  const total = slices.reduce((sum, s) => sum + s.value, 0)
  const config = Object.fromEntries(slices.map((s) => [s.key, { label: s.label, color: s.color }])) satisfies ChartConfig
  const data = total > 0 ? slices.filter((s) => s.value > 0) : [{ key: 'empty', label: 'None', value: 1, color: 'var(--muted)' }]

  return (
    <div className="relative size-22 shrink-0">
      <ChartContainer config={config} className="relative z-10 aspect-square size-22">
        <PieChart>
          {/* Tooltip hiện ngay tại chỗ (không trượt theo chuột) và nằm trên số ở giữa vòng tròn. */}
          {total > 0 && (
            <ChartTooltip
              isAnimationActive={false}
              wrapperStyle={{ zIndex: 20 }}
              content={<ChartTooltipContent nameKey="key" hideLabel />}
            />
          )}
          <Pie
            data={data}
            dataKey="value"
            nameKey="key"
            innerRadius={30}
            outerRadius={44}
            paddingAngle={total > 0 && data.length > 1 ? 2 : 0}
            strokeWidth={0}
            isAnimationActive={false}
          >
            {data.map((s) => (
              <Cell key={s.key} fill={s.color} />
            ))}
          </Pie>
        </PieChart>
      </ChartContainer>
      <div className="pointer-events-none absolute inset-0 z-0 flex flex-col items-center justify-center">
        <span className="text-lg leading-tight font-semibold tabular-nums">{total}</span>
        <span className="text-[10px] text-muted-foreground">{centerLabel}</span>
      </div>
    </div>
  )
}
