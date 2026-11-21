import type { Timeline, VideoFinding } from '@/api/videos'

// bbox là [x, y, w, h] tính bằng pixel trên khung gốc của ảnh.
export type Bbox = [number, number, number, number]

export type Keyframe = {
  id: string // đường dẫn trong timeline, ví dụ "frames/000015.jpg"
  t: number
  ocr: { text: string; bbox: Bbox }[]
  faces: { label: string; bbox: Bbox }[] // khuôn mặt khớp ảnh mẫu của đối tượng
  refImages: { label: string; bbox: Bbox }[] // ảnh mẫu (logo, chân dung quen thuộc) khớp
}

// Gom keyframe và OCR của timeline theo từng khung; khung bao khuôn mặt/ảnh mẫu lấy từ triggers của nghi vấn.
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
    const name = entityNames[f.entity] ?? f.entity
    for (const tr of f.triggers) {
      if ((tr.via !== 'face' && tr.via !== 'ref_image') || !tr.frame || !tr.bbox) continue
      // Khung đã có trong timeline (frames/ocr) thì dùng đúng t của khung đó; chỉ khung ngoài timeline
      // (ví dụ thumbnail "sources/…") mới tạm lấy thời điểm của nghi vấn.
      const k = get(tr.frame, f.start ?? 0)
      const match = { label: name, bbox: tr.bbox as Bbox }
      ;(tr.via === 'face' ? k.faces : k.refImages).push(match)
    }
  }
  return [...frames.values()].sort((a, b) => a.t - b.t)
}
