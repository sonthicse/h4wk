import { useEffect, useRef, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { formatTime, inSpans } from '@/lib/findings'
import { cn } from '@/lib/utils'
import { frameUrl, type VideoFinding } from '@/api/videos'
import type { Bbox, Keyframe } from './keyframes'
import type { PlayerControls } from './usePlayer'

const boxStyle = {
  ocr: { label: 'OCR text', color: 'border-yellow-400 text-yellow-300' },
  face: { label: 'Face match', color: 'border-red-500 text-red-400' },
  ref: { label: 'Reference image match', color: 'border-cyan-400 text-cyan-300' },
}

const LABEL_ROOM = 28

const DEFAULT_SIZE = { w: 854, h: 480 }

export function BoxLayer({ frame, size }: { frame: Keyframe; size: { w: number; h: number } }) {
  const all = [
    ...frame.ocr.map((b) => ({ ...b, kind: 'ocr' as const })),
    ...frame.faces.map((b) => ({ ...b, text: b.label, kind: 'face' as const })),
    ...frame.refImages.map((b) => ({ ...b, text: b.label, kind: 'ref' as const })),
  ]
  const pos = ([x, y, w, h]: Bbox) => ({
    left: `${(x / size.w) * 100}%`,
    top: `${(y / size.h) * 100}%`,
    width: `${(w / size.w) * 100}%`,
    height: `${(h / size.h) * 100}%`,
  })
  return (
    <>
      {all.map((b, i) => (
        <div key={i} className={cn('absolute border-2', boxStyle[b.kind].color)} style={pos(b.bbox)}>
          <span
            className={cn(
              'absolute left-[-2px] bg-black/70 px-1 text-[11px] whitespace-nowrap',

              b.kind === 'face' ? 'bottom-0' : b.bbox[1] < LABEL_ROOM ? 'top-0' : '-top-5',
            )}
          >
            {b.text}
          </span>
        </div>
      ))}
    </>
  )
}

export function BoxLegend() {
  return (
    <ul className="flex flex-wrap gap-3 text-xs">
      {Object.values(boxStyle).map((s) => (
        <li key={s.label} className="flex items-center gap-1">
          <span className={cn('size-3 border-2', s.color)} />
          {s.label}
        </li>
      ))}
    </ul>
  )
}

export function FrameImage({
  frame,
  src,
  boxes = false,
  className,
}: {
  frame: Keyframe
  src: string
  boxes?: boolean
  className?: string
}) {
  const [size, setSize] = useState(DEFAULT_SIZE)
  const [broken, setBroken] = useState(false)
  return (
    <div className={cn('relative aspect-video overflow-hidden rounded bg-zinc-800', className)}>
      {broken ? (
        <span className="absolute inset-0 flex items-center justify-center text-xs text-zinc-400">Image unavailable</span>
      ) : (
        <img
          src={src}
          alt={`Keyframe at ${formatTime(frame.t)}`}
          loading="lazy"
          className="size-full object-fill"
          onLoad={(e) => setSize({ w: e.currentTarget.naturalWidth || DEFAULT_SIZE.w, h: e.currentTarget.naturalHeight || DEFAULT_SIZE.h })}
          onError={() => setBroken(true)}
        />
      )}
      <span className="absolute right-1 bottom-1 font-mono text-[10px] text-white/60">frame @ {formatTime(frame.t)}</span>
      {boxes && <BoxLayer frame={frame} size={size} />}
    </div>
  )
}

export default function KeyframeStrip({
  videoId,
  capture,
  keyframes,
  findings,
  player,
}: {
  videoId: string
  capture?: string
  keyframes: Keyframe[]
  findings: VideoFinding[]
  player: PlayerControls
}) {
  const src = (k: Keyframe) => frameUrl(videoId, k.id, capture)
  const listRef = useRef<HTMLDivElement>(null)
  const playing = [...keyframes].reverse().find((k) => k.t <= player.currentTime)

  useEffect(() => {
    const box = listRef.current
    const el = box?.querySelector<HTMLElement>('[data-playing="true"]')
    if (!box || !el) return
    const strip = box.getBoundingClientRect()
    const frame = el.getBoundingClientRect()
    if (frame.left < strip.left || frame.right > strip.right) {
      box.scrollLeft += frame.left - strip.left - (box.clientWidth - frame.width) / 2
    }
  }, [playing?.id])

  if (keyframes.length === 0) {
    return (
      <section aria-label="Keyframes" className="space-y-2">
        <h2 className="text-sm font-medium">Keyframes</h2>
        <p className="text-sm text-muted-foreground">No keyframes. They are only extracted at capture level full, once the video has been analysed.</p>
      </section>
    )
  }

  return (
    <section aria-label="Keyframes" className="space-y-2">
      <h2 className="text-sm font-medium">Keyframes</h2>
      <div ref={listRef} className="relative flex gap-2 overflow-x-auto pb-2">
        {keyframes.map((k) => {
          const flagged = findings.some((f) => inSpans(f, k.t))
          const isPlaying = k.id === playing?.id
          return (
            <button
              key={k.id}
              type="button"
              data-playing={isPlaying}
              aria-label={`Keyframe at ${formatTime(k.t)}`}
              onClick={() => player.seek(k.t)}
              className={cn(
                'w-32 shrink-0 space-y-1 rounded p-1 text-left hover:bg-muted focus-visible:bg-muted focus-visible:outline-none',
                isPlaying && 'bg-muted ring-2 ring-primary',
              )}
            >
              <FrameImage frame={k} src={src(k)} />
              <span className="flex items-center justify-between font-mono text-xs text-muted-foreground">
                {formatTime(k.t)}
                {flagged && <Badge variant="destructive" className="h-4 text-[10px]">flagged</Badge>}
              </span>
            </button>
          )
        })}
      </div>
    </section>
  )
}
