import { Badge } from '@/components/ui/badge'
import { HoverHighlight, HoverItem } from '@/components/ui/hover-highlight'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import type { Severity, VideoFinding } from '@/api/videos'
import { formatTime, inSpans, mergeKey, severityRank, severityVariant, timedSources } from '@/lib/findings'
import { cn } from '@/lib/utils'
import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import type { PlayerControls } from './usePlayer'

const MAX_GROUPS = 10

type Group = { key: string; first: VideoFinding; count: number; severity: Severity; ids: Set<string> }

// Gộp nghi vấn cùng nguồn và cùng quote (khoá bỏ dấu); dòng đại diện là nghi vấn sớm nhất của nhóm.
function groupFindings(list: VideoFinding[]): Group[] {
  const map = new Map<string, Group>()
  for (const f of list) {
    const key = `${f.sourceKind}:${mergeKey(f.quote)}`
    const g = map.get(key)
    if (!g) {
      map.set(key, { key, first: f, count: 1, severity: f.severity, ids: new Set([f.id]) })
      continue
    }
    g.count++
    g.ids.add(f.id)
    if (severityRank[f.severity] < severityRank[g.severity]) g.severity = f.severity
    if (f.start !== null && (g.first.start === null || f.start < g.first.start)) g.first = f
  }
  return [...map.values()]
}

// Mốc thời gian của nghi vấn; nguồn không có mốc (tiêu đề, mô tả, thumbnail, comment) thì '—'.
const isTimed = (f: VideoFinding) => timedSources.has(f.sourceKind) && f.start !== null
const timeRange = (f: VideoFinding) => (isTimed(f) ? `${formatTime(f.start!)}–${formatTime(f.end ?? f.start!)}` : '—')

const severityColor: Record<Severity, string> = {
  high: 'bg-red-500',
  medium: 'bg-amber-500',
  low: 'bg-sky-500',
}

// Thanh thời gian: tô mọi đoạn nghi vấn xuất hiện theo severity; bấm vào thanh để seek,
// bấm vào một đoạn để mở nghi vấn và nhảy tới đầu đoạn đó − 2s.
export default function FindingTimeline({
  findings,
  player,
  activeId,
  onOpen,
}: {
  findings: VideoFinding[]
  player: PlayerControls
  activeId: string | null
  onOpen: (f: VideoFinding, at?: number) => void
}) {
  const { duration, currentTime } = player
  const timed = findings.filter(isTimed).sort((a, b) => a.start! - b.start!)
  const untimed = findings.filter((f) => !isTimed(f))
  const groups = groupFindings([...timed, ...untimed])
  const listRef = useRef<HTMLUListElement>(null)
  // Nhóm nào có đoạn đang nằm dưới đầu phát thì được tô và tự cuộn vào tầm nhìn.
  const nowKey = groups.find((g) => [...g.ids].some((id) => {
    const f = findings.find((x) => x.id === id)
    return f !== undefined && isTimed(f) && inSpans(f, currentTime)
  }))?.key
  useEffect(() => {
    const box = listRef.current
    const row = box?.querySelector<HTMLElement>('[data-now="true"]')
    if (!box || !row) return
    box.scrollTo({ top: row.offsetTop - box.clientHeight / 3, behavior: 'smooth' })
  }, [nowKey])
  const [showAll, setShowAll] = useState(false)
  const shown = showAll ? groups : groups.slice(0, MAX_GROUPS)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium">Timeline</h2>
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
        {duration > 0 && timed.flatMap((f) => f.spans.map((s, i) => (
          <Tooltip key={`${f.id}:${i}`}>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label={`Finding at ${formatTime(s.start)}–${formatTime(s.end)}: ${f.quote}`}
                className={cn(
                  'absolute inset-y-0 min-w-1.5 rounded-sm opacity-80 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-1',
                  severityColor[f.severity],
                  f.id === activeId && 'opacity-100 ring-2 ring-foreground',
                )}
                style={{
                  left: `${(s.start / duration) * 100}%`,
                  width: `${((s.end - s.start) / duration) * 100}%`,
                }}
                onClick={(e) => {
                  e.stopPropagation()
                  onOpen(f, s.start)
                }}
              />
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="font-mono text-xs">
                {formatTime(s.start)}–{formatTime(s.end)} · {f.sourceKind}
                {f.spans.length > 1 && ` · ${i + 1} of ${f.spans.length} places`}
              </p>
              <p>{f.quote}</p>
            </TooltipContent>
          </Tooltip>
        )))}
        <div
          className="pointer-events-none absolute inset-y-[-3px] w-0.5 bg-foreground"
          style={{ left: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
        />
      </div>

      <div className="flex items-center gap-2">
        <h2 className="text-sm font-medium">Findings</h2>
        <span className="text-xs text-muted-foreground">sorted by time · the one under the playhead is highlighted</span>
      </div>
      {findings.length === 0 ? (
        <p className="text-sm text-muted-foreground">No findings in this video.</p>
      ) : (
        <HoverHighlight>
          <ul ref={listRef} className="max-h-72 space-y-1 overflow-y-auto">
            {shown.map(({ key, first: f, count, severity, ids }) => (
              <HoverItem key={key}>
                <button
                  type="button"
                  data-now={key === nowKey}
                  onClick={() => onOpen(f)}
                  className={cn(
                    'flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm focus-visible:bg-muted focus-visible:outline-none',
                    (key === nowKey || (activeId !== null && ids.has(activeId))) && 'bg-muted',
                  )}
                >
                  <Badge variant={severityVariant[severity]}>{severity}</Badge>
                  <span className="w-44 shrink-0 font-mono text-xs text-muted-foreground">
                    {timeRange(f)} · {f.sourceKind}
                  </span>
                  <span className="shrink-0 text-xs text-muted-foreground">{f.category}</span>
                  <span className="truncate">{f.quote}</span>
                  {count > 1 && (
                    <Badge variant="outline" className="ml-auto shrink-0">×{count}</Badge>
                  )}
                </button>
              </HoverItem>
            ))}
          </ul>
          {groups.length > MAX_GROUPS && (
            <Button variant="ghost" size="sm" onClick={() => setShowAll((v) => !v)}>
              {showAll ? 'Show less' : `Show all (${groups.length})`}
            </Button>
          )}
        </HoverHighlight>
      )}
    </div>
  )
}
