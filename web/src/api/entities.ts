import { api, type Schemas } from '@/api/client'

export type Entity = Schemas['EntityOut']
export type RefImage = Schemas['RefImage']
export type RefKind = RefImage['kind']
export type EntityPatch = Schemas['EntityUpdate']

// Danh sách đối tượng, kèm số ảnh mẫu mỗi loại (ref_counts).
export function listEntities(): Promise<Entity[]> {
  return api('/api/entities')
}

export function createEntity(
  name: string,
  aliases: string[] = [],
  abbreviations: string[] = [],
  description = '',
): Promise<Entity> {
  return api('/api/entities', { method: 'POST', body: { name, aliases, abbreviations, description } })
}

export function updateEntity(id: string, patch: EntityPatch): Promise<Entity> {
  return api(`/api/entities/${encodeURIComponent(id)}`, { method: 'PATCH', body: patch })
}

export function listRefs(id: string): Promise<Record<RefKind, RefImage[]>> {
  return api(`/api/entities/${encodeURIComponent(id)}/refs`)
}

// Gửi nguyên bytes ảnh (JPEG/PNG/WebP, tối đa 10 MB); tải trùng ảnh thì backend trả lại ảnh cũ.
export function uploadRef(id: string, kind: RefKind, file: File): Promise<RefImage> {
  return api(`/api/entities/${encodeURIComponent(id)}/refs/${kind}`, { method: 'POST', body: file })
}

export function deleteRef(ref: RefImage): Promise<void> {
  return api(ref.url, { method: 'DELETE' })
}
