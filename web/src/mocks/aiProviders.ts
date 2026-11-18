// API giả cho trang Settings → AI providers (SPEC 10.10 mục 6–7, hợp đồng C5).
// Thay bằng API thật của T32 khi có. Server không bao giờ trả key đầy đủ, chỉ trả bản đã che.

export type AiTask = 'analysis.classify' | 'analysis.classify_comment' | 'media.vision'
export type ProviderType = 'anthropic' | 'openai_compat' | 'gemini'

export const AI_TASKS: AiTask[] = ['analysis.classify', 'analysis.classify_comment', 'media.vision']

export type AiModel = { name: string; vision: boolean; structured: boolean }

export type AiProvider = {
  name: string
  type: ProviderType
  baseUrl: string | null // chỉ có với openai_compat
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

// "Server" giữ key thật ở đây; chỉ hàm mask() đi ra ngoài.
const secrets: Record<string, string> = {
  anthropic: 'sk-ant-api03-demo-000000000000007f3a',
  openai: 'sk-proj-demo-0000000000000000c19e',
  deepseek: 'sk-demo-00000000000000000000b42d',
  glm: 'sk-demo-glm-expired-0000000000e5a1',
}

let providers: Omit<AiProvider, 'apiKeyMasked'>[] = [
  {
    name: 'anthropic',
    type: 'anthropic',
    baseUrl: null,
    models: [
      { name: 'claude-sonnet-5-5', vision: true, structured: true },
      { name: 'claude-haiku-5-5', vision: true, structured: true },
    ],
  },
  {
    name: 'openai',
    type: 'openai_compat',
    baseUrl: 'https://api.openai.com/v1',
    models: [
      { name: 'gpt-5', vision: true, structured: true },
      { name: 'gpt-5-mini', vision: true, structured: true },
    ],
  },
  {
    name: 'gemini',
    type: 'gemini',
    baseUrl: null,
    models: [
      { name: 'gemini-3-pro', vision: true, structured: true },
      { name: 'gemini-3-flash', vision: true, structured: true },
    ],
  },
  {
    name: 'deepseek',
    type: 'openai_compat',
    baseUrl: 'https://api.deepseek.com',
    models: [
      { name: 'deepseek-chat', vision: false, structured: false },
      { name: 'deepseek-reasoner', vision: false, structured: false },
    ],
  },
  {
    name: 'qwen',
    type: 'openai_compat',
    baseUrl: 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1',
    models: [
      { name: 'qwen-max', vision: false, structured: true },
      { name: 'qwen-vl-max', vision: true, structured: false },
    ],
  },
  {
    name: 'glm',
    type: 'openai_compat',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    models: [
      { name: 'glm-4.6', vision: false, structured: true },
      { name: 'glm-4.5v', vision: true, structured: false },
    ],
  },
  {
    name: 'kimi',
    type: 'openai_compat',
    baseUrl: 'https://api.moonshot.ai/v1',
    models: [{ name: 'kimi-k2', vision: false, structured: true }],
  },
]

// qwen chưa có key nên analysis.classify_comment hiện cảnh báo "không còn model dùng được".
let tasks: Record<AiTask, AiRoute[]> = {
  'analysis.classify': [
    { provider: 'anthropic', model: 'claude-sonnet-5-5' },
    { provider: 'deepseek', model: 'deepseek-chat' },
  ],
  'analysis.classify_comment': [{ provider: 'qwen', model: 'qwen-max' }],
  'media.vision': [
    { provider: 'gemini', model: 'gemini-3-flash' },
    { provider: 'anthropic', model: 'claude-sonnet-5-5' },
  ],
}

function mask(key: string) {
  return `${key.slice(0, 3)}…${key.slice(-4)}`
}

function snapshot(): AiSettings {
  return structuredClone({
    providers: providers.map((p) => ({ ...p, apiKeyMasked: secrets[p.name] ? mask(secrets[p.name]) : null })),
    tasks,
  })
}

function delay<T>(value: T, ms = 300): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), ms))
}

export function getAiSettings(): Promise<AiSettings> {
  return delay(snapshot())
}

export function saveAiSettings(input: AiSettingsInput): Promise<AiSettings> {
  for (const p of input.providers) {
    if (p.newApiKey) secrets[p.name] = p.newApiKey
  }
  // Nhà cung cấp bị xoá thì key của nó cũng bị xoá.
  for (const name of Object.keys(secrets)) {
    if (!input.providers.some((p) => p.name === name)) delete secrets[name]
  }
  providers = input.providers.map(({ name, type, baseUrl, models }) => ({ name, type, baseUrl, models }))
  tasks = structuredClone(input.tasks)
  return delay(snapshot(), 500)
}

// Gọi thử một request nhỏ tới nhà cung cấp bằng cấu hình đã lưu.
export function testProvider(name: string): Promise<ProviderTestResult> {
  let result: ProviderTestResult
  if (!secrets[name]) result = { ok: false, message: 'No API key set.' }
  else if (secrets[name].includes('expired')) result = { ok: false, message: '401 Unauthorized: invalid or expired API key.' }
  else result = { ok: true, message: 'Connected', latencyMs: 300 + Math.round(Math.random() * 600) }
  return delay(result, 1200)
}
