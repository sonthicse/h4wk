import { useEffect, useState } from 'react'
import type { Timeline, VideoFinding } from '@/api/videos'

export type Bbox = [number, number, number, number]

export type Keyframe = {
  id: string
  t: number
  ocr: { text: string; bbox: Bbox }[]
  faces: { label: string; bbox: Bbox }[]
  refImages: { label: string; bbox: Bbox }[]
}

export function buildKeyframes(timeline: Timeline | null | undefined, findings: VideoFinding[], entityNames: Record<string, string>): Keyframe[] {
  const frames = new Map<string, Keyframe>()
  const get = (id: string, t: number) => {
    let k = frames.get(id)
    if (!k) frames.set(id, (k = { id, t, ocr: [], faces: [], refImages: [] }))
    return k
  }
  for (const seg of timeline?.segments ?? []) {
    for (const o of seg.ocr ?? []) get(o.frame, o.t).ocr.push({ text: o.text, bbox: o.bbox as Bbox })
    for (const fr of seg.frames ?? []) get(fr.frame, fr.t)
  }
  for (const f of findings) {
    const name = f.entity ? (entityNames[f.entity] ?? f.entity) : f.category
    for (const tr of f.triggers) {
      if ((tr.via !== 'face' && tr.via !== 'ref_image') || !tr.frame || !tr.bbox) continue

      const k = get(tr.frame, f.start ?? 0)
      const match = { label: name, bbox: tr.bbox as Bbox }
      ;(tr.via === 'face' ? k.faces : k.refImages).push(match)
    }
  }
  return [...frames.values()].sort((a, b) => a.t - b.t)
}

export const BOX_WINDOW_S = 1

export function nearestKeyframe(keyframes: Keyframe[], t: number): Keyframe | null {
  let best: Keyframe | null = null
  for (const k of keyframes) {
    if (Math.abs(k.t - t) <= BOX_WINDOW_S && (!best || Math.abs(k.t - t) < Math.abs(best.t - t))) best = k
  }
  return best
}

export const DEFAULT_FRAME_SIZE = { w: 854, h: 480 }

export function useFrameSize(src: string | null) {
  const [size, setSize] = useState(DEFAULT_FRAME_SIZE)
  useEffect(() => {
    if (!src) return
    const img = new Image()
    img.onload = () => setSize({ w: img.naturalWidth || DEFAULT_FRAME_SIZE.w, h: img.naturalHeight || DEFAULT_FRAME_SIZE.h })
    img.src = src
  }, [src])
  return size
}
