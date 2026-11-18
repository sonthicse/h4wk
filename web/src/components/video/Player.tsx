import { Pause, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatTime } from '@/lib/findings'
import type { Finding } from '@/mocks/data'
import type { PlayerControls } from './usePlayer'

// Trình phát giả: khung 16:9 placeholder, nút play/pause và thanh seek.
export default function Player({ player, activeFinding }: { player: PlayerControls; activeFinding: Finding | null }) {
  const { currentTime, duration, playing } = player
  const inFinding = activeFinding && activeFinding.end > activeFinding.start && currentTime >= activeFinding.start && currentTime <= activeFinding.end

  return (
    <div className="space-y-2">
      <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-lg bg-zinc-900 text-zinc-400">
        <div className="text-center">
          <p className="font-mono text-5xl text-zinc-200">{formatTime(currentTime)}</p>
          <p className="mt-2 text-xs">Simulated player · proxy 480p</p>
        </div>
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
          value={currentTime}
          onChange={(e) => player.seek(Number(e.target.value))}
        />
        <span className="w-24 text-right font-mono text-sm text-muted-foreground">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>
    </div>
  )
}
