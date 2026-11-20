import { Pause, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { VideoFinding } from '@/api/videos'
import { formatTime, inSpans } from '@/lib/findings'
import type { PlayerControls, VideoProps } from './usePlayer'

// Trình phát thật trên <video>; không có media (hoặc nạp lỗi) thì hiện khung trống, thanh seek vẫn dùng được cho transcript/timeline.
export default function Player({
  player,
  videoProps,
  src,
  failed,
  activeFinding,
}: {
  player: PlayerControls
  videoProps: VideoProps
  src: string | null
  failed: boolean
  activeFinding: VideoFinding | null
}) {
  const { currentTime, duration, playing } = player
  const hasMedia = src !== null && !failed
  const inFinding = activeFinding && inSpans(activeFinding, currentTime)

  return (
    <div className="space-y-2">
      <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-lg bg-zinc-900 text-zinc-400">
        {hasMedia ? (
          <video {...videoProps} src={src} preload="metadata" playsInline className="size-full bg-black object-contain" />
        ) : (
          <div className="px-4 text-center text-sm">
            <p className="text-zinc-200">No video file</p>
            <p className="mt-1 text-xs">
              {failed ? 'The media file could not be loaded.' : 'Media is only stored at capture level full.'}
            </p>
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
        <input
          type="range"
          aria-label="Seek"
          className="h-2 flex-1 cursor-pointer accent-primary"
          min={0}
          max={duration}
          step={0.5}
          disabled={duration <= 0}
          value={Math.min(currentTime, duration)}
          onChange={(e) => player.seek(Number(e.target.value))}
        />
        <span className="w-24 text-right font-mono text-sm text-muted-foreground">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>
    </div>
  )
}
