// Ảnh mẫu giả của đối tượng (SPEC 10.1, T39). Đối tượng lấy từ API thật (/api/entities); backend chưa có API
// ảnh mẫu nên phần ảnh còn giả, gắn theo id đối tượng. Ảnh thật sẽ nằm ở data/entities/<entity_id>/refs/{face,image}/.
// Ảnh người dùng tải lên chỉ tạo object URL trong trình duyệt, không gửi đi đâu.

export type RefKind = 'face' | 'image'

export type RefImage = {
  id: string
  entityId: string
  kind: RefKind
  filename: string
  url: string | null
  uploadedAt: string
}

// Bắt đầu rỗng: đối tượng là dữ liệu thật, nên không gắn sẵn ảnh giả vào id của chúng.
let store: RefImage[] = []

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
