// API giả cho trang Settings → Sources (T33). Thay bằng API thật của T32 khi có.
// Tên nguồn và loại dữ liệu bám đúng enum trong hợp đồng C5 (docs/contracts/c5-sources.json).

export type SourceName = 'ytdlp' | 'youtube_api' | 'supadata'

export type Cap =
  | 'video.metadata'
  | 'channel.metadata'
  | 'channel.videos'
  | 'playlist.videos'
  | 'video.transcripts'
  | 'video.comments'
  | 'video.thumbnails'
  | 'video.media'

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

// Quota YouTube đếm theo ngày, credit Supadata đếm theo tháng (SPEC 10.3).
export type Usage = { used: number; limit: number; unit: 'units' | 'credits'; period: 'day' | 'month'; resetsAt: string }

// Dữ liệu trả về giao diện. Key chỉ có dạng đã che, không có trường nào chứa key đầy đủ.
export type Source = {
  name: SourceName
  enabled: boolean
  needsKey: boolean
  maskedKey: string | null
  state: 'active' | 'paused'
  pausedUntil: string | null
  consecutiveFailures: number
  lastError: string | null
  usage: Usage | null
}

export type SourcesSettings = {
  sources: Source[]
  // Mỗi loại dữ liệu chỉ liệt kê các nguồn lấy được loại đó, theo thứ tự ưu tiên.
  priority: Record<Cap, SourceName[]>
}

export type SourcesUpdate = {
  enabled: Record<SourceName, boolean>
  priority: Record<Cap, SourceName[]>
  // Key mới nhập để thay key cũ; nguồn nào không có trong đây thì giữ key cũ.
  keys: Partial<Record<SourceName, string>>
}

export type TestResult = { ok: boolean; message: string; testedAt: string }

const MIN = 60_000

// Nửa đêm giờ Thái Bình Dương tiếp theo. Tháng 11 là giờ PST (UTC−8), tức 15:00 giờ Việt Nam.
function nextPacificMidnight() {
  const d = new Date()
  d.setUTCHours(8, 0, 0, 0)
  if (d.getTime() <= Date.now()) d.setUTCDate(d.getUTCDate() + 1)
  return d.toISOString()
}

function firstOfNextMonthVn() {
  const now = new Date()
  const year = now.getUTCMonth() === 11 ? now.getUTCFullYear() + 1 : now.getUTCFullYear()
  const month = String(((now.getUTCMonth() + 1) % 12) + 1).padStart(2, '0')
  return `${year}-${month}-01T00:00:00+07:00`
}

// Key đầy đủ chỉ nằm trong "server" giả này.
const secrets: Partial<Record<SourceName, string>> = {
  youtube_api: 'AIzaSyD4demoOnlyKeyNotReal9k3Q',
  supadata: 'sd_live_demoOnlyKey7f21',
}

function mask(key: string | undefined) {
  if (!key) return null
  // Key quá ngắn thì che hết để không lộ phần lớn key.
  if (key.length < 12) return '••••'
  return `${key.slice(0, 3)}…${key.slice(-4)}`
}

type StoredSource = Omit<Source, 'maskedKey'>

const store: { sources: StoredSource[]; priority: Record<Cap, SourceName[]> } = {
  sources: [
    {
      name: 'ytdlp',
      enabled: true,
      needsKey: false,
      // Bị chặn 5 lần liên tiếp nên tạm ngưng 30 phút; đã trôi qua khoảng 10 phút.
      state: 'paused',
      pausedUntil: new Date(Date.now() + 20 * MIN).toISOString(),
      consecutiveFailures: 5,
      lastError: "Blocked: Sign in to confirm you're not a bot.",
      usage: null,
    },
    {
      name: 'youtube_api',
      enabled: true,
      needsKey: true,
      state: 'active',
      pausedUntil: null,
      consecutiveFailures: 0,
      lastError: null,
      usage: { used: 3412, limit: 10000, unit: 'units', period: 'day', resetsAt: nextPacificMidnight() },
    },
    {
      name: 'supadata',
      enabled: true,
      needsKey: true,
      state: 'active',
      pausedUntil: null,
      consecutiveFailures: 0,
      lastError: null,
      usage: { used: 37, limit: 100, unit: 'credits', period: 'month', resetsAt: firstOfNextMonthVn() },
    },
  ],
  // Giống config/sources.toml.example.
  priority: {
    'video.metadata': ['youtube_api', 'ytdlp', 'supadata'],
    'channel.metadata': ['youtube_api', 'ytdlp'],
    'channel.videos': ['youtube_api', 'ytdlp'],
    'playlist.videos': ['youtube_api', 'ytdlp'],
    'video.transcripts': ['ytdlp', 'supadata'],
    'video.comments': ['youtube_api', 'ytdlp'],
    'video.thumbnails': ['ytdlp', 'youtube_api'],
    'video.media': ['ytdlp'],
  },
}

function delay<T>(value: T, ms = 150): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), ms))
}

function snapshot(): SourcesSettings {
  return {
    sources: store.sources.map((s) => ({ ...s, maskedKey: mask(secrets[s.name]) })),
    priority: structuredClone(store.priority),
  }
}

export function getSourcesSettings(): Promise<SourcesSettings> {
  return delay(snapshot())
}

// Trả về cấu hình mới để giao diện cập nhật ngay, không phải chờ tải lại.
export function saveSourcesSettings(update: SourcesUpdate): Promise<SourcesSettings> {
  for (const s of store.sources) s.enabled = update.enabled[s.name]
  store.priority = structuredClone(update.priority)
  for (const [name, key] of Object.entries(update.keys)) {
    if (key) secrets[name as SourceName] = key
  }
  return delay(snapshot(), 400)
}

// Bật lại nguồn đang tạm ngưng: xoá bộ đếm lỗi liên tiếp.
export function resumeSource(name: SourceName): Promise<void> {
  const s = store.sources.find((x) => x.name === name)
  if (s) Object.assign(s, { state: 'active', pausedUntil: null, consecutiveFailures: 0 })
  return delay(undefined)
}

// Kiểm tra kết nối bằng key đã lưu (không dùng key đang gõ dở).
export function testSource(name: SourceName): Promise<TestResult> {
  const testedAt = new Date().toISOString()
  let result: Omit<TestResult, 'testedAt'>
  if (name === 'ytdlp') {
    result = { ok: false, message: "Blocked: Sign in to confirm you're not a bot. (HTTP 429)" }
  } else if (!secrets[name]) {
    result = { ok: false, message: 'No API key saved.' }
  } else if (name === 'youtube_api') {
    result = { ok: true, message: 'Connected. videos.list returned 1 item (1 quota unit, 184 ms).' }
  } else {
    result = { ok: true, message: 'Connected. Account has 63 credits left this month (212 ms).' }
  }
  return delay({ ...result, testedAt }, 1200)
}
