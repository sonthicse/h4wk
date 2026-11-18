// API đối tượng và ảnh mẫu giả cho trang Entities (SPEC 10.1, T39). Thay bằng API thật của T39 khi có.
// Ảnh mẫu thật sẽ nằm ở data/cases/<case>/entities/<entity_id>/refs/{face,image}/.
// Ở bản giả, ảnh có sẵn không có file (url = null, giao diện vẽ ô placeholder);
// ảnh người dùng tải lên chỉ tạo object URL trong trình duyệt, không gửi đi đâu.

export type RefKind = 'face' | 'image'

export type RefImage = {
  id: string
  kind: RefKind
  filename: string
  url: string | null
  uploadedAt: string
}

export type Entity = {
  id: string
  caseId: string
  name: string
  aliases: string[]
  abbreviations: string[]
  refs: RefImage[]
}

export type EntityPatch = Pick<Entity, 'name' | 'aliases' | 'abbreviations'>

const store: Entity[] = [
  {
    id: 'e_01',
    caseId: 'c_demo',
    name: 'Nguyễn Văn A',
    aliases: ['ông A', 'anh Văn A'],
    abbreviations: ['NVA'],
    refs: [
      { id: 'r_01', kind: 'face', filename: 'face_front.jpg', url: null, uploadedAt: '2026-11-10T09:00:00+07:00' },
      { id: 'r_02', kind: 'face', filename: 'face_side.jpg', url: null, uploadedAt: '2026-11-10T09:01:00+07:00' },
      { id: 'r_03', kind: 'image', filename: 'portrait_press.jpg', url: null, uploadedAt: '2026-11-10T09:05:00+07:00' },
    ],
  },
  {
    id: 'e_02',
    caseId: 'c_demo',
    name: 'Công ty B',
    aliases: ['Cty B', 'B Group'],
    abbreviations: ['CTB'],
    refs: [
      { id: 'r_04', kind: 'image', filename: 'logo_b.png', url: null, uploadedAt: '2026-11-10T09:10:00+07:00' },
      { id: 'r_05', kind: 'image', filename: 'logo_b_2019.png', url: null, uploadedAt: '2026-11-10T09:11:00+07:00' },
    ],
  },
  {
    id: 'e_01',
    caseId: 'c_trial',
    name: 'Trần Thị C',
    aliases: ['bà C'],
    abbreviations: [],
    refs: [],
  },
]

function delay<T>(value: T): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), 150))
}

function find(caseId: string, entityId: string) {
  const entity = store.find((e) => e.caseId === caseId && e.id === entityId)
  if (!entity) throw new Error(`Entity ${entityId} not found`)
  return entity
}

// Trả bản sao để component không sửa trực tiếp vào store.
function copy(e: Entity): Entity {
  return { ...e, aliases: [...e.aliases], abbreviations: [...e.abbreviations], refs: [...e.refs] }
}

export function listEntities(caseId: string): Promise<Entity[]> {
  return delay(store.filter((e) => e.caseId === caseId).map(copy))
}

export function createEntity(caseId: string, name: string): Promise<Entity> {
  // ID đối tượng đánh số trong từng case: e_01, e_02, …
  const n = store.filter((e) => e.caseId === caseId).length + 1
  const entity: Entity = {
    id: `e_${n.toString().padStart(2, '0')}`,
    caseId,
    name,
    aliases: [],
    abbreviations: [],
    refs: [],
  }
  store.push(entity)
  return delay(copy(entity))
}

export function updateEntity(caseId: string, entityId: string, patch: EntityPatch): Promise<Entity> {
  const entity = find(caseId, entityId)
  Object.assign(entity, patch)
  return delay(copy(entity))
}

export function addRefImages(caseId: string, entityId: string, kind: RefKind, files: File[]): Promise<RefImage[]> {
  const entity = find(caseId, entityId)
  const added = files.map(
    (file, i): RefImage => ({
      id: `r_${Date.now()}_${i}`,
      kind,
      filename: file.name,
      url: URL.createObjectURL(file),
      uploadedAt: new Date().toISOString(),
    }),
  )
  entity.refs.push(...added)
  return delay(added)
}

export function deleteRefImage(caseId: string, entityId: string, refId: string): Promise<void> {
  const entity = find(caseId, entityId)
  const ref = entity.refs.find((r) => r.id === refId)
  if (ref?.url) URL.revokeObjectURL(ref.url)
  entity.refs = entity.refs.filter((r) => r.id !== refId)
  return delay(undefined)
}
