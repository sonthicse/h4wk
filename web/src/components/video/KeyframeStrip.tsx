import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { formatTime } from '@/lib/findings'
import { cn } from '@/lib/utils'
import type { Finding } from '@/mocks/data'
import { FRAME_H, FRAME_W, type Bbox, type Keyframe } from '@/mocks/videos'
import type { PlayerControls } from './usePlayer'

// Ba loại khung bao, mỗi loại một màu (có chú giải bên dưới ảnh).
const boxStyle = {
  ocr: { label: 'OCR text', color: 'border-yellow-400 text-yellow-300' },
  face: { label: 'Face match', color: 'border-red-500 text-red-400' },
  ref: { label: 'Reference image match', color: 'border-cyan-400 text-cyan-300' },
}

// Chiều cao (px khung 480p) tối thiểu phía trên box để đặt nhãn.
const LABEL_ROOM = 28

// Ảnh giả của một khung hình: nền màu theo hue, kèm các khung bao nếu `boxes`.
function FrameImage({ frame, boxes = false, className }: { frame: Keyframe; boxes?: boolean; className?: string }) {
  const all = [
    ...frame.ocr.map((b) => ({ ...b, kind: 'ocr' as const })),
    ...frame.faces.map((b) => ({ ...b, text: b.label, kind: 'face' as const })),
    ...frame.refImages.map((b) => ({ ...b, text: b.label, kind: 'ref' as const })),
  ]
  const pos = ([x, y, w, h]: Bbox) => ({
    left: `${(x / FRAME_W) * 100}%`,
    top: `${(y / FRAME_H) * 100}%`,
    width: `${(w / FRAME_W) * 100}%`,
    height: `${(h / FRAME_H) * 100}%`,
  })
  return (
    <div
      className={cn('relative aspect-video overflow-hidden rounded', className)}
      style={{ background: `linear-gradient(135deg, hsl(${frame.hue} 45% 28%), hsl(${frame.hue + 40} 40% 14%))` }}
    >
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
  keyframes,
  findings,
  player,
  activeFinding,
}: {
  keyframes: Keyframe[]
  findings: Finding[]
  player: PlayerControls
  activeFinding: Finding | null
}) {
  const [pickedId, setPickedId] = useState<string | null>(null)

  // Khi mở bằng ?finding= thì mặc định chọn khung nằm trong đoạn nghi vấn đó.
  const inFinding = activeFinding && keyframes.find((k) => k.t >= activeFinding.start && k.t <= activeFinding.end)
  const selected = keyframes.find((k) => k.id === pickedId) ?? inFinding ?? null
  const playing = [...keyframes].reverse().find((k) => k.t <= player.currentTime)

  if (keyframes.length === 0) {
    return (
      <section className="space-y-2">
        <h2 className="text-sm font-medium">Keyframes</h2>
        <p className="text-sm text-muted-foreground">No keyframes. They are only extracted at capture level full.</p>
      </section>
    )
  }

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium">Keyframes</h2>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {keyframes.map((k) => {
          const flagged = findings.some((f) => k.t >= f.start && k.t <= f.end && f.end > f.start)
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
              <FrameImage frame={k} />
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
        <div className="grid grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-4 rounded-lg border p-3">
          <div className="space-y-2">
            <FrameImage frame={selected} boxes className="w-full" />
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
