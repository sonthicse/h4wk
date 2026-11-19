import { useEffect, useRef, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { Transcript, VideoFinding } from '@/api/videos'
import { formatTime } from '@/lib/findings'
import { cn } from '@/lib/utils'
import type { PlayerControls } from './usePlayer'

// Transcript tự cuộn theo thời gian phát; bấm một đoạn để seek.
export default function TranscriptPane({
  transcripts,
  findings,
  player,
  activeId,
}: {
  transcripts: Transcript[]
  findings: VideoFinding[]
  player: PlayerControls
  activeId: string | null
}) {
  const [kind, setKind] = useState<string>(transcripts[0]?.kind ?? '')
  const listRef = useRef<HTMLDivElement>(null)
  const transcript = transcripts.find((t) => t.kind === kind) ?? transcripts[0]

  const activeIndex = transcript?.segments.findIndex((s) => player.currentTime >= s.start && player.currentTime < s.end) ?? -1

  // Cuộn riêng trong khung transcript (không dùng scrollIntoView để khỏi kéo cả trang).
  useEffect(() => {
    const box = listRef.current
    const row = box?.querySelector<HTMLElement>('[data-active="true"]')
    if (!box || !row) return
    box.scrollTo({ top: row.offsetTop - box.clientHeight / 3, behavior: 'smooth' })
  }, [activeIndex, kind])

  return (
    <div className="flex h-full min-h-0 flex-col rounded-lg border">
      <div className="flex items-center justify-between gap-2 border-b p-3">
        <h2 className="text-sm font-medium">Transcript</h2>
        {transcript && (
          <Select value={transcript.kind} onValueChange={setKind}>
            <SelectTrigger size="sm" className="w-40" aria-label="Transcript type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {transcripts.map((t) => (
                <SelectItem key={t.kind} value={t.kind}>{t.kind}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {!transcript ? (
        <p className="p-4 text-sm text-muted-foreground">No transcript was collected for this video.</p>
      ) : (
        <div ref={listRef} className="relative min-h-0 flex-1 overflow-y-auto p-2">
          {transcript.segments.map((s, i) => {
            const flagged = findings.filter(
              (f) => f.start !== null && f.end !== null && f.start < s.end && f.end > s.start && f.end > f.start,
            )
            const isActive = i === activeIndex
            const isTarget = flagged.some((f) => f.id === activeId)
            return (
              <button
                key={s.start}
                type="button"
                data-active={isActive}
                onClick={() => player.seek(s.start)}
                className={cn(
                  'block w-full rounded border-l-2 border-transparent px-2 py-1.5 text-left text-sm hover:bg-muted focus-visible:bg-muted focus-visible:outline-none',
                  flagged.length > 0 && 'border-l-destructive bg-destructive/5',
                  isTarget && 'ring-1 ring-destructive',
                  isActive && 'bg-primary/10 font-medium',
                )}
              >
                <span className="mb-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-mono">{formatTime(s.start)}</span>
                  <Badge variant="outline" className="h-4 text-[10px]">{transcript.kind}</Badge>
                  {flagged.length > 0 && <Badge variant="destructive" className="h-4 text-[10px]">flagged</Badge>}
                </span>
                {s.text}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
