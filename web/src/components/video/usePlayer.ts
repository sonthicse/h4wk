import { useEffect, useState } from 'react'

// Giao diện của trình phát. Khi có video thật, chỉ cần viết lại hook này trên thẻ <video>
// (currentTime = video.currentTime, seek = gán video.currentTime, play/pause = video.play()/pause()).
export type PlayerControls = {
  currentTime: number
  playing: boolean
  duration: number
  seek: (t: number) => void
  play: () => void
  pause: () => void
}

// Bản giả: thời gian tăng theo đồng hồ khi đang phát.
export function usePlayer(duration: number, initialTime = 0, autoplay = false): PlayerControls {
  const [currentTime, setCurrentTime] = useState(initialTime)
  const [playing, setPlaying] = useState(autoplay)

  useEffect(() => {
    if (!playing) return
    const timer = setInterval(() => {
      setCurrentTime((t) => {
        const next = t + 0.25
        if (next >= duration) {
          setPlaying(false)
          return duration
        }
        return next
      })
    }, 250)
    return () => clearInterval(timer)
  }, [playing, duration])

  const seek = (t: number) => setCurrentTime(Math.min(Math.max(t, 0), duration))
  const play = () => {
    if (currentTime >= duration) setCurrentTime(0)
    setPlaying(true)
  }
  return { currentTime, playing, duration, seek, play, pause: () => setPlaying(false) }
}
