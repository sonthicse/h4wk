import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { formatTime, inSpans } from '@/lib/findings'
import { cn } from '@/lib/utils'
import { frameUrl, type VideoFinding } from '@/api/videos'
import type { Bbox, Keyframe } from './keyframes'
import type { PlayerControls } from './usePlayer'

// Ba loại khung bao, mỗi loại một màu (có chú giải bên dưới ảnh).
const boxStyle = {
  ocr: { label: 'OCR text', color: 'border-yellow-400 text-yellow-300' },
  face: { label: 'Face match', color: 'border-red-500 text-red-400' },
  ref: { label: 'Reference image match', color: 'border-cyan-400 text-cyan-300' },
}

// Chiều cao (px khung 480p) tối thiểu phía trên box để đặt nhãn.
const LABEL_ROOM = 28

// Kích thước khung khi chưa đọc được ảnh (bản proxy 480p).
const DEFAULT_SIZE = { w: 854, h: 480 }

// Ảnh keyframe thật, kèm các khung bao nếu `boxes`. Bbox tính theo pixel của ảnh nên quy về % theo kích thước thật.
function FrameImage({
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
      {boxes &&
        all.map((b, i) => (
          <div key={i} className={cn('absolute border-2', boxStyle[b.kind].color)} style={pos(b.bbox)}>
            <span
              className={cn(
                'absolute left-[-2px] bg-black/70 px-1 text-[11px] whitespace-nowrap',
                // Nhãn khuôn mặt nằm trong box, ở đáy, để không đè nhãn của ảnh mẫu bao quanh khuôn mặt.
                b.kind === 'face' ? 'bottom-0' : b.bbox[1] < LABEL_ROOM ? 'top-0' : '-top-5', // sát mép trên thì đặt vào trong box
              )}
            >
              {b.text}
            </span>
          </div>
        ))}
    </div>
  )
}

// Dải keyframe. Bấm một khung: seek tới khung đó và hiện ảnh lớn kèm khung bao và mô tả.
export default function KeyframeStrip({
  videoId,
  capture,
  keyframes,
  findings,
  player,
  activeFinding,
}: {
  videoId: string
  capture?: string
  keyframes: Keyframe[]
  findings: VideoFinding[]
  player: PlayerControls
  activeFinding: VideoFinding | null
}) {
  const src = (k: Keyframe) => frameUrl(videoId, k.id, capture)
  const inRange = (k: Keyframe, f: VideoFinding) => inSpans(f, k.t)
  const [pickedId, setPickedId] = useState<string | null>(null)

  // Khi mở bằng ?finding= thì mặc định chọn khung nằm trong đoạn nghi vấn đó.
  const inFinding = activeFinding && (keyframes.find((k) => k.id === activeFinding.frame) ?? keyframes.find((k) => inRange(k, activeFinding)))
  const selected = keyframes.find((k) => k.id === pickedId) ?? inFinding ?? null
  const playing = [...keyframes].reverse().find((k) => k.t <= player.currentTime)

  if (keyframes.length === 0) {
    return (
      <section className="space-y-2">
        <h2 className="text-sm font-medium">Keyframes</h2>
        <p className="text-sm text-muted-foreground">No keyframes. They are only extracted at capture level full, once the video has been analysed.</p>
      </section>
    )
  }

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium">Keyframes</h2>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {keyframes.map((k) => {
          const flagged = findings.some((f) => f.frame === k.id || inRange(k, f))
          return (
            <button
              key={k.id}
              type="button"
              aria-label={`Keyframe at ${formatTime(k.t)}`}
              onClick={() => {
                setPickedId(k.id)
                player.seek(k.t)
              }}
              className={cn(
                'w-32 shrink-0 space-y-1 rounded p-1 text-left hover:bg-muted focus-visible:bg-muted focus-visible:outline-none',
                k.id === selected?.id && 'bg-muted ring-2 ring-primary',
              )}
            >
              <FrameImage frame={k} src={src(k)} />
              <span className="flex items-center justify-between font-mono text-xs text-muted-foreground">
                {formatTime(k.t)}
                {flagged && <Badge variant="destructive" className="h-4 text-[10px]">flagged</Badge>}
                {!flagged && k.id === playing?.id && <span>now</span>}
              </span>
            </button>
          )
        })}
      </div>

      {selected ? (
        <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-4 rounded-lg border p-3">
          <div className="space-y-2">
            <FrameImage frame={selected} src={src(selected)} boxes className="w-full" />
            <ul className="flex flex-wrap gap-3 text-xs">
              {Object.values(boxStyle).map((s) => (
                <li key={s.label} className="flex items-center gap-1">
                  <span className={cn('size-3 border-2', s.color)} />
                  {s.label}
                </li>
              ))}
            </ul>
          </div>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">VLM description</dt>
              <dd>{selected.visual?.description ?? 'Not analysed.'}</dd>
              {selected.visual && (
                <dd className="font-mono text-xs text-muted-foreground">
                  {selected.visual.provider}/{selected.visual.model}
                </dd>
              )}
            </div>
            {selected.visual && selected.visual.offensiveCues.length > 0 && (
              <div>
                <dt className="text-xs text-muted-foreground">Offensive cues</dt>
                <dd className="mt-1 flex flex-wrap gap-1">
                  {selected.visual.offensiveCues.map((c) => (
                    <Badge key={c} variant="destructive">{c}</Badge>
                  ))}
                </dd>
              </div>
            )}
            <div>
              <dt className="text-xs text-muted-foreground">OCR text</dt>
              <dd>
                {selected.ocr.length === 0 ? (
                  <span className="text-muted-foreground">No text detected.</span>
                ) : (
                  <ul className="space-y-1">
                    {selected.ocr.map((o) => (
                      <li key={o.text} className="font-mono text-xs">{o.text}</li>
                    ))}
                  </ul>
                )}
              </dd>
            </div>
            {(selected.faces.length > 0 || selected.refImages.length > 0) && (
              <div>
                <dt className="text-xs text-muted-foreground">Matched references</dt>
                <dd className="space-y-1">
                  {[...selected.faces, ...selected.refImages].map((m) => (
                    <p key={m.label}>{m.label}</p>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Select a keyframe to see OCR, face and reference matches.</p>
      )}
    </section>
  )
}
