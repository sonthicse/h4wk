import type { AiProvider, AiRoute, AiSettings, AiSettingsInput, AiTask } from '@/mocks/aiProviders'

// Bản nháp đang sửa trên trang. Key mới gõ vào chỉ nằm ở newApiKey cho tới khi Save.
export type DraftProvider = AiProvider & { newApiKey: string }
export type Draft = { providers: DraftProvider[]; tasks: Record<AiTask, AiRoute[]> }

export function toDraft(s: AiSettings): Draft {
  return structuredClone({ providers: s.providers.map((p) => ({ ...p, newApiKey: '' })), tasks: s.tasks })
}

export function toInput(d: Draft): AiSettingsInput {
  return {
    providers: d.providers.map(({ name, type, baseUrl, models, newApiKey }) => ({
      name,
      type,
      baseUrl,
      models,
      newApiKey: newApiKey.trim() || undefined,
    })),
    tasks: d.tasks,
  }
}

export const hasKey = (p: DraftProvider) => Boolean(p.apiKeyMasked || p.newApiKey.trim())

// So một nhà cung cấp trong bản nháp với bản đã lưu (không tính key vì key đã lưu không về tới đây).
export function providerChanged(p: DraftProvider, saved: AiProvider | undefined) {
  if (!saved) return true
  const fields = (x: AiProvider) => JSON.stringify([x.type, x.baseUrl, x.models])
  return p.newApiKey.trim() !== '' || fields(p) !== fields(saved)
}

export function validBaseUrl(url: string | null) {
  if (!url) return false
  try {
    const u = new URL(url)
    return u.protocol === 'https:' || u.protocol === 'http:'
  } catch {
    return false
  }
}

// Model có được gán cho tác vụ này không (media.vision chỉ nhận model có vision).
export const modelAllowed = (task: AiTask, m: { vision: boolean }) => task !== 'media.vision' || m.vision

// Lý do một dòng (provider, model) không dùng được. blocking = cấu hình sai, server sẽ từ chối nên chặn Save;
// không blocking = cấu hình hợp lệ nhưng lúc chạy sẽ bị bỏ qua (ví dụ chưa có key).
export type RouteProblem = { reason: string; blocking: boolean }

export function routeProblem(task: AiTask, route: AiRoute, providers: DraftProvider[]): RouteProblem | null {
  const p = providers.find((x) => x.name === route.provider)
  if (!p) return { reason: 'Provider removed', blocking: true }
  const m = p.models.find((x) => x.name === route.model)
  if (!m) return { reason: 'Model removed', blocking: true }
  if (!modelAllowed(task, m)) return { reason: 'Model has no vision', blocking: true }
  if (!hasKey(p)) return { reason: 'No API key', blocking: false }
  return null
}

// Các lỗi chặn Save, hiện thành danh sách phía trên trang.
export function draftErrors(d: Draft): string[] {
  const errors: string[] = []
  for (const p of d.providers) {
    if (p.type === 'openai_compat' && !validBaseUrl(p.baseUrl)) errors.push(`${p.name}: base URL must be an http(s) URL.`)
  }
  for (const [task, routes] of Object.entries(d.tasks) as [AiTask, AiRoute[]][]) {
    if (routes.length === 0) errors.push(`${task}: add at least one provider and model.`)
    routes.forEach((r, i) => {
      const problem = routeProblem(task, r, d.providers)
      if (problem?.blocking) errors.push(`${task} #${i + 1}: ${problem.reason.toLowerCase()}.`)
    })
  }
  return errors
}
