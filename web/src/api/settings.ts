import { api, type Schemas } from '@/api/client'

export type SourcesSettings = Schemas['SourcesSettings']
export type SourceInfo = Schemas['SourceInfo']
export type SourceName = SourceInfo['name']
export type Cap = Schemas['Cap']
export type TestResult = Schemas['TestResult']
export type KeyInfo = Schemas['KeyInfo']

// Thứ tự hiển thị các loại dữ liệu.
export const caps: Cap[] = [
  'video.metadata',
  'channel.metadata',
  'channel.videos',
  'playlist.videos',
  'video.transcripts',
  'video.comments',
  'video.thumbnails',
  'video.media',
]

export const sourceLabel: Record<SourceName, string> = {
  ytdlp: 'yt-dlp',
  youtube_api: 'YouTube Data API',
  supadata: 'Supadata',
}

const source = (name: SourceName) => `/api/settings/sources/${encodeURIComponent(name)}`

export function getSourcesSettings(): Promise<SourcesSettings> {
  return api('/api/settings/sources')
}

export function putSourcesSettings(body: Schemas['SourcesUpdate']): Promise<SourcesSettings> {
  return api('/api/settings/sources', { method: 'PUT', body })
}

export function setSourceKey(name: SourceName, value: string): Promise<KeyInfo> {
  return api(`${source(name)}/key`, { method: 'PUT', body: { value } })
}

export function testSource(name: SourceName): Promise<TestResult> {
  return api(`${source(name)}/test`, { method: 'POST' })
}

export function resumeSource(name: SourceName): Promise<SourceInfo> {
  return api(`${source(name)}/resume`, { method: 'POST' })
}

// ---- AI providers (T34) ----
// Kiểu dạng UI: models là mảng, tên trường camelCase. Hàm bên dưới đổi qua lại với dạng API.

export type AiTask = 'analysis.video_verdict' | 'media.vision'
// Tương thích tạm với trang cũ trong lúc T62 thay Settings AI.
export type ProviderType = 'anthropic' | 'openai_compat' | 'gemini' | 'ollama'
type LegacyAiSettings = {
  providers: { name: string; type: ProviderType; base_url: string | null; models: Record<string, Omit<AiModel, 'name'>>; key: { masked?: string | null } }[]
  tasks: Partial<Record<AiTask, AiRoute[]>>
}

export const AI_TASKS: AiTask[] = ['analysis.video_verdict', 'media.vision']

export type AiModel = { name: string; vision: boolean; structured: boolean }

export type AiProvider = {
  name: string
  type: ProviderType
  baseUrl: string | null // chỉ có với openai_compat và ollama
  models: AiModel[]
  apiKeyMasked: string | null // dạng sk-…abcd; null nghĩa là chưa có key
}

export type AiRoute = { provider: string; model: string }

export type AiSettings = {
  providers: AiProvider[]
  tasks: Record<AiTask, AiRoute[]>
}

// Dữ liệu gửi lên khi Save: key mới (nếu có) chỉ đi một chiều từ trình duyệt lên server.
export type AiSettingsInput = {
  providers: (Omit<AiProvider, 'apiKeyMasked'> & { newApiKey?: string })[]
  tasks: Record<AiTask, AiRoute[]>
}

export type ProviderTestResult = { ok: boolean; message: string; latencyMs?: number }

const provider = (name: string) => `/api/settings/ai/providers/${encodeURIComponent(name)}`

export async function getAiSettings(): Promise<AiSettings> {
  const data = await api<LegacyAiSettings>('/api/settings/ai')
  return {
    providers: data.providers.map((p) => ({
      name: p.name,
      type: p.type,
      baseUrl: p.base_url,
      models: Object.entries(p.models).map(([name, caps]) => ({ name, vision: caps.vision, structured: caps.structured })),
      apiKeyMasked: p.key.masked ?? null,
    })),
    tasks: Object.fromEntries(AI_TASKS.map((t) => [t, data.tasks[t] ?? []])) as AiSettings['tasks'],
  }
}

// Thứ tự: ghi cấu hình (backend tự xoá key của provider bị gỡ), đặt key mới, rồi tải lại.
export async function saveAiSettings(input: AiSettingsInput): Promise<AiSettings> {
  await api('/api/settings/ai', {
    method: 'PUT',
    body: {
      providers: Object.fromEntries(
        input.providers.map((p) => [
          p.name,
          {
            type: p.type,
            ...(p.baseUrl ? { base_url: p.baseUrl } : {}),
            models: Object.fromEntries(p.models.map((m) => [m.name, { vision: m.vision, structured: m.structured }])),
          },
        ]),
      ),
      tasks: Object.fromEntries(Object.entries(input.tasks).filter(([, routes]) => routes.length > 0)),
    },
  })
  for (const p of input.providers) {
    if (p.newApiKey) await api(`${provider(p.name)}/key`, { method: 'PUT', body: { value: p.newApiKey } })
  }
  return getAiSettings()
}

export async function testProvider(name: string): Promise<ProviderTestResult> {
  const r = await api<Schemas['TestResult']>(`${provider(name)}/test`, { method: 'POST', body: {} })
  return { ok: r.ok, message: r.detail, latencyMs: r.latency_ms ?? undefined }
}

// ---- Jev (TypeSafe, T47): phân loại lời nói và comment. Kiểu viết tay, chưa có trong schema.d.ts (không chạy gen:api). ----
export function getJevSettings(): Promise<{ key: KeyInfo }> {
  return api('/api/settings/jev')
}

export function setJevKey(value: string): Promise<KeyInfo> {
  return api('/api/settings/jev/key', { method: 'PUT', body: { value } })
}

export function deleteJevKey(): Promise<KeyInfo> {
  return api('/api/settings/jev/key', { method: 'DELETE' })
}
