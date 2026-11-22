import { useState } from 'react'
import { Pause, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { VideoFinding } from '@/api/videos'
import { formatTime, inSpans } from '@/lib/findings'
import { frameUrl } from '@/api/videos'
import { BoxLayer, BoxLegend } from './KeyframeStrip'
import { nearestKeyframe, useFrameSize, type Keyframe } from './keyframes'
import type { PlayerControls, VideoProps } from './usePlayer'
import { cn } from '@/lib/utils'

const severityBar = { high: 'bg-red-500/60', medium: 'bg-amber-500/60', low: 'bg-sky-500/60' }

export default function Player({
  player,
  videoProps,
  src,
  failed,
  activeFinding,
  videoId,
  capture,
  keyframes,
  findings,
}: {
  videoId: string
  capture?: string
  keyframes: Keyframe[]
  findings: VideoFinding[]
  player: PlayerControls
  videoProps: VideoProps
  src: string | null
  failed: boolean
  activeFinding: VideoFinding | null
}) {
  const { currentTime, duration, playing } = player
  const hasMedia = src !== null && !failed
  const inFinding = activeFinding && inSpans(activeFinding, currentTime)
  const [boxesOn, setBoxesOn] = useState(true)
  const [videoRatio, setVideoRatio] = useState(0)
  const near = nearestKeyframe(keyframes, currentTime)
  const hasBoxes = near !== null && near.ocr.length + near.faces.length + near.refImages.length > 0
  const size = useFrameSize(near ? frameUrl(videoId, near.id, capture) : null)

  return (
    <div className="space-y-2">
      <div className="relative flex aspect-video [container-type:size] items-center justify-center overflow-hidden rounded-lg bg-zinc-900 text-zinc-400">
        {hasMedia ? (
          <video {...videoProps} src={src} preload="metadata" playsInline onLoadedMetadata={(event) => {
            videoProps.onLoadedMetadata(event)
            const { videoWidth, videoHeight } = event.currentTarget
            setVideoRatio(videoHeight ? videoWidth / videoHeight : 0)
          }} className="size-full bg-black object-contain" />
        ) : (
          <div className="px-4 text-center text-sm">
            <p className="text-zinc-200">No video file</p>
            <p className="mt-1 text-xs">
              {failed ? 'The media file could not be loaded.' : 'Media is only stored at capture level full.'}
            </p>
          </div>
        )}
        {hasMedia && videoRatio > 0 && boxesOn && near && hasBoxes && (
          <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 overflow-hidden"
            data-video-overlay
            style={{ width: `min(100cqw, ${videoRatio * 100}cqh)`, aspectRatio: videoRatio }}>
            <BoxLayer frame={near} size={size} />
            <span className="absolute top-2 right-2 rounded bg-black/55 px-1.5 font-mono text-[11px] text-zinc-50">
              keyframe {formatTime(near.t)}
            </span>
          </div>
        )}
        {inFinding && (
          <p className="absolute inset-x-3 bottom-3 rounded bg-black/70 px-3 py-2 text-sm text-white">
            {activeFinding.quote}
          </p>
        )}
      </div>
      <div className="flex items-center gap-3">
        <Button
          size="icon"
          variant="outline"
          aria-label={playing ? 'Pause' : 'Play'}
          disabled={!hasMedia}
          onClick={playing ? player.pause : player.play}
        >
          {playing ? <Pause /> : <Play />}
        </Button>
        <div className="relative flex h-2 flex-1 items-center">
        {duration > 0 &&
          findings.flatMap((f) =>
            f.spans.filter((sp) => sp.end > sp.start).map((sp, i) => (
              <span
                key={`${f.id}:${i}`}
                aria-hidden="true"
                className={cn('pointer-events-none absolute inset-y-[-2px] rounded-sm', severityBar[f.severity])}
                style={{ left: `${(sp.start / duration) * 100}%`, width: `${((sp.end - sp.start) / duration) * 100}%` }}
              />
            )),
          )}
        <input
          type="range"
          aria-label="Seek"
          className="relative h-2 w-full cursor-pointer accent-primary"
          min={0}
          max={duration}
          step={0.5}
          disabled={duration <= 0}
          value={Math.min(currentTime, duration)}
          onChange={(e) => player.seek(Number(e.target.value))}
        />
        </div>
        <Button size="sm" variant="outline" aria-pressed={boxesOn} onClick={() => setBoxesOn((v) => !v)}>
          Boxes {boxesOn ? 'on' : 'off'}
        </Button>
        <span className="w-24 text-right font-mono text-sm text-muted-foreground">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <BoxLegend />
        <span className="ml-auto">Boxes show while the video is within 1 s of a keyframe</span>
      </div>
    </div>
  )
}
