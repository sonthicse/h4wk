import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import type { Severity, VideoFinding } from '@/api/videos'
import { formatTime, severityVariant, timedSources } from '@/lib/findings'
import { cn } from '@/lib/utils'
import type { PlayerControls } from './usePlayer'

// Mốc thời gian của nghi vấn; nguồn không có mốc (tiêu đề, mô tả, thumbnail, comment) thì '—'.
const isTimed = (f: VideoFinding) => timedSources.has(f.sourceKind) && f.start !== null
const timeRange = (f: VideoFinding) => (isTimed(f) ? `${formatTime(f.start!)}–${formatTime(f.end ?? f.start!)}` : '—')

const severityColor: Record<Severity, string> = {
  high: 'bg-red-500',
  medium: 'bg-amber-500',
  low: 'bg-sky-500',
}

// Thanh thời gian: tô đoạn có nghi vấn theo severity; bấm vào thanh để seek, bấm vào đoạn để nhảy tới start − 2s.
export default function FindingTimeline({
  findings,
  player,
  activeId,
  onOpen,
}: {
  findings: VideoFinding[]
  player: PlayerControls
  activeId: string | null
  onOpen: (f: VideoFinding) => void
}) {
  const { duration, currentTime } = player
  const timed = findings.filter(isTimed)
  const untimed = findings.filter((f) => !isTimed(f))

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium">Findings timeline</h2>
        <div className="flex gap-3 text-xs text-muted-foreground">
          {(['high', 'medium', 'low'] as const).map((s) => (
            <span key={s} className="flex items-center gap-1">
              <span className={cn('size-2 rounded-full', severityColor[s])} />
              {s}
            </span>
          ))}
        </div>
      </div>

      <div
        className="relative h-8 cursor-pointer rounded bg-muted"
        onClick={(e) => {
          const box = e.currentTarget.getBoundingClientRect()
          if (duration > 0) player.seek(((e.clientX - box.left) / box.width) * duration)
        }}
      >
        {duration > 0 && timed.map((f) => (
          <Tooltip key={f.id}>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label={`Finding at ${timeRange(f)}: ${f.quote}`}
                className={cn(
                  'absolute inset-y-0 min-w-1.5 rounded-sm opacity-80 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-1',
                  severityColor[f.severity],
                  f.id === activeId && 'opacity-100 ring-2 ring-foreground',
                )}
                style={{
                  left: `${(f.start! / duration) * 100}%`,
                  width: `${(((f.end ?? f.start!) - f.start!) / duration) * 100}%`,
                }}
                onClick={(e) => {
                  e.stopPropagation()
                  onOpen(f)
                }}
              />
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="font-mono text-xs">{timeRange(f)} · {f.sourceKind}</p>
              <p>{f.quote}</p>
            </TooltipContent>
          </Tooltip>
        ))}
        <div
          className="pointer-events-none absolute inset-y-[-3px] w-0.5 bg-foreground"
          style={{ left: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
        />
      </div>

      {findings.length === 0 ? (
        <p className="text-sm text-muted-foreground">No findings in this video.</p>
      ) : (
        <ul className="space-y-1">
          {[...timed, ...untimed].map((f) => (
            <li key={f.id}>
              <button
                type="button"
                onClick={() => onOpen(f)}
                className={cn(
                  'flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm hover:bg-muted focus-visible:bg-muted focus-visible:outline-none',
                  f.id === activeId && 'bg-muted',
                )}
              >
                <Badge variant={severityVariant[f.severity]}>{f.severity}</Badge>
                <span className="w-44 shrink-0 font-mono text-xs text-muted-foreground">
                  {timeRange(f)} · {f.sourceKind}
                </span>
                <span className="truncate">{f.quote}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
