import { useRef, useState, type SyntheticEvent } from 'react'

// Giao diện của trình phát; các thành phần khác (transcript, thanh nghi vấn, keyframe) chỉ dùng phần này.
export type PlayerControls = {
  currentTime: number
  playing: boolean
  duration: number
  seek: (t: number) => void
  play: () => void
  pause: () => void
}

// Phần gắn vào thẻ <video> thật.
export type VideoProps = {
  ref: React.RefObject<HTMLVideoElement | null>
  onLoadedMetadata: (e: SyntheticEvent<HTMLVideoElement>) => void
  onTimeUpdate: (e: SyntheticEvent<HTMLVideoElement>) => void
  onPlay: () => void
  onPause: () => void
  onError: () => void
}

// Hook trên thẻ <video>: currentTime = video.currentTime, seek = gán video.currentTime.
// `durationHint` (từ metadata) dùng khi chưa có media; có media thì lấy độ dài thật của file.
export function usePlayer(durationHint: number, initialTime = 0, autoplay = false) {
  const ref = useRef<HTMLVideoElement>(null)
  const target = useRef(initialTime) // vị trí muốn tới; áp dụng khi media nạp xong nếu seek quá sớm
  const [currentTime, setCurrentTime] = useState(initialTime)
  const [playing, setPlaying] = useState(false)
  const [mediaDuration, setMediaDuration] = useState(0)
  const [failed, setFailed] = useState(false)
  const duration = mediaDuration || durationHint

  const seek = (t: number) => {
    const next = Math.max(duration > 0 ? Math.min(t, duration) : t, 0)
    target.current = next
    setCurrentTime(next)
    const el = ref.current
    if (el && el.readyState > 0) el.currentTime = next
  }

  const videoProps: VideoProps = {
    ref,
    onLoadedMetadata: (e) => {
      const el = e.currentTarget
      setMediaDuration(Number.isFinite(el.duration) ? el.duration : 0)
      if (target.current > 0) el.currentTime = target.current
      // Trình duyệt có thể chặn tự phát; khi đó người dùng bấm Play.
      if (autoplay) el.play().catch(() => {})
    },
    onTimeUpdate: (e) => setCurrentTime(e.currentTarget.currentTime),
    onPlay: () => setPlaying(true),
    onPause: () => setPlaying(false),
    onError: () => setFailed(true),
  }

  const controls: PlayerControls = {
    currentTime,
    playing,
    duration,
    seek,
    play: () => void ref.current?.play().catch(() => {}),
    pause: () => ref.current?.pause(),
  }
  return { controls, videoProps, failed }
}
