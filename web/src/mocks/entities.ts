// Ảnh mẫu giả của đối tượng (SPEC 10.1, T39). Đối tượng lấy từ API thật (/api/entities); backend chưa có API
// ảnh mẫu nên phần ảnh còn giả, gắn theo id đối tượng. Ảnh thật sẽ nằm ở data/entities/<entity_id>/refs/{face,image}/.
// Ảnh có sẵn không có file (url = null, giao diện vẽ ô placeholder);
// ảnh người dùng tải lên chỉ tạo object URL trong trình duyệt, không gửi đi đâu.

export type RefKind = 'face' | 'image'

export type RefImage = {
  id: string
  entityId: string
  kind: RefKind
  filename: string
  url: string | null
  uploadedAt: string
}

let store: RefImage[] = [
  { id: 'r_01', entityId: 'e_01', kind: 'face', filename: 'face_front.jpg', url: null, uploadedAt: '2026-11-10T09:00:00+07:00' },
  { id: 'r_02', entityId: 'e_01', kind: 'face', filename: 'face_side.jpg', url: null, uploadedAt: '2026-11-10T09:01:00+07:00' },
  { id: 'r_03', entityId: 'e_01', kind: 'image', filename: 'portrait_press.jpg', url: null, uploadedAt: '2026-11-10T09:05:00+07:00' },
  { id: 'r_04', entityId: 'e_02', kind: 'image', filename: 'logo_b.png', url: null, uploadedAt: '2026-11-10T09:10:00+07:00' },
  { id: 'r_05', entityId: 'e_02', kind: 'image', filename: 'logo_b_2019.png', url: null, uploadedAt: '2026-11-10T09:11:00+07:00' },
]

function delay<T>(value: T): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), 150))
}

// Mọi ảnh mẫu của mọi đối tượng.
export function listRefImages(): Promise<RefImage[]> {
  return delay([...store])
}

export function addRefImages(entityId: string, kind: RefKind, files: File[]): Promise<RefImage[]> {
  const added = files.map(
    (file, i): RefImage => ({
      id: `r_${Date.now()}_${i}`,
      entityId,
      kind,
      filename: file.name,
      url: URL.createObjectURL(file),
      uploadedAt: new Date().toISOString(),
    }),
  )
  store.push(...added)
  return delay(added)
}

export function deleteRefImage(refId: string): Promise<void> {
  const ref = store.find((r) => r.id === refId)
  if (ref?.url) URL.revokeObjectURL(ref.url)
  store = store.filter((r) => r.id !== refId)
  return delay(undefined)
}
