// API bản thu (capture) giả cho trang Capture / Evidence (T29). Tên trường bám theo manifest
// trong hợp đồng C1 (docs/contracts/c1-manifest.json), đổi sang camelCase.
// Thay bằng API thật `api/captures.py` khi có.
import { findings } from '@/mocks/data'
import type { CollectLevel } from '@/mocks/jobs'

export type Cap =
  | 'video.metadata'
  | 'channel.metadata'
  | 'channel.videos'
  | 'playlist.videos'
  | 'video.transcripts'
  | 'video.comments'
  | 'video.thumbnails'
  | 'video.media'

export type SourceStatus =
  | 'ok'
  | 'failed'
  | 'blocked'
  | 'quota_exceeded'
  | 'not_found'
  | 'unsupported'
  | 'disabled'
  | 'suspended'
  | 'no_source'

export type SourceCall = {
  provider: string | null // null khi status là no_source
  what: Cap
  status: SourceStatus
  startedAt?: string
  durationMs?: number
  cost?: { quotaUnits?: number; credits?: number }
  error?: string
  version?: string
}

export type FileEntry = { sha256: string; bytes: number }

export type Manifest = {
  schema: 'h4wk.manifest/1'
  sourceUrl: string
  collectedAt: string
  collector: string // `user:<tên>` hoặc `system:watchlist:<watch_item>`
  trigger: { type: 'manual' | 'watchlist'; watchItem?: string; event?: string }
  level: CollectLevel
  toolVersion: string
  sources: SourceCall[]
  files: Record<string, FileEntry> // khoá là đường dẫn tương đối trong thư mục bản thu
  previousCapture: string | null
}

export type Capture = {
  id: string // YYYYMMDDTHHMMSS, cũng là tên thư mục bản thu
  caseId: string
  videoId: string
  videoTitle: string
  manifest: Manifest
}

export type VerifyStatus = 'OK' | 'FAIL' | 'missing' | 'unexpected'

export type VerifyFile = {
  path: string
  status: VerifyStatus
  expected?: FileEntry // theo manifest; không có với file `unexpected`
  actual?: FileEntry // tính lại từ đĩa; không có với file `missing`
}

export type VerifyResult = { captureId: string; checkedAt: string; files: VerifyFile[] }

// SHA-256 giả nhưng cố định (64 ký tự hex) để dữ liệu giả trông như thật.
function fakeSha256(seed: string) {
  let h = 2166136261
  let out = ''
  while (out.length < 64) {
    for (const ch of seed + out.length) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0
    out += h.toString(16).padStart(8, '0')
  }
  return out.slice(0, 64)
}

function files(captureId: string, list: [path: string, bytes: number][]): Record<string, FileEntry> {
  return Object.fromEntries(list.map(([path, bytes]) => [path, { sha256: fakeSha256(captureId + path), bytes }]))
}

const YTDLP = '2026.10.26'

const captures: Capture[] = [
  // Thu thủ công, mọi nguồn chạy tốt. Verify: tất cả OK.
  {
    id: '20261117T213000',
    caseId: 'c_demo',
    videoId: 'dQw4w9WgXcQ',
    videoTitle: '',
    manifest: {
      schema: 'h4wk.manifest/1',
      sourceUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      collectedAt: '2026-11-17T21:30:00+07:00',
      collector: 'user:thi',
      trigger: { type: 'manual' },
      level: 'full',
      toolVersion: 'h4wk 0.1.0',
      sources: [
        { provider: 'youtube_api', what: 'video.metadata', status: 'ok', startedAt: '2026-11-17T21:30:01+07:00', durationMs: 412, cost: { quotaUnits: 1 } },
        { provider: 'youtube_api', what: 'channel.metadata', status: 'ok', startedAt: '2026-11-17T21:30:02+07:00', durationMs: 298, cost: { quotaUnits: 1 } },
        { provider: 'ytdlp', what: 'video.transcripts', status: 'ok', startedAt: '2026-11-17T21:30:03+07:00', durationMs: 2140, version: YTDLP },
        { provider: 'youtube_api', what: 'video.comments', status: 'ok', startedAt: '2026-11-17T21:30:05+07:00', durationMs: 3870, cost: { quotaUnits: 4 } },
        { provider: 'ytdlp', what: 'video.thumbnails', status: 'ok', startedAt: '2026-11-17T21:30:09+07:00', durationMs: 960, version: YTDLP },
        { provider: 'ytdlp', what: 'video.media', status: 'ok', startedAt: '2026-11-17T21:30:10+07:00', durationMs: 48200, version: YTDLP },
      ],
      files: files('20261117T213000', [
        ['normalized.json', 18342],
        ['sources/youtube_api/video.json', 6120],
        ['sources/youtube_api/channel.json', 3407],
        ['sources/youtube_api/comments.json', 412880],
        ['sources/ytdlp/dQw4w9WgXcQ.vi.vtt', 21544],
        ['sources/ytdlp/dQw4w9WgXcQ.vi-orig.vtt', 23019],
        ['sources/ytdlp/maxres.jpg', 148213],
        ['sources/ytdlp/dQw4w9WgXcQ.mp4', 182334112],
      ]),
      previousCapture: null,
    },
  },
  // Thu lại cùng video: yt-dlp bị chặn nên chuyển nguồn; video không còn nguồn nào (no_source).
  // Verify: 1 FAIL, 1 missing, 1 unexpected (xem verifyProblems bên dưới).
  {
    id: '20261118T091200',
    caseId: 'c_demo',
    videoId: 'dQw4w9WgXcQ',
    videoTitle: '',
    manifest: {
      schema: 'h4wk.manifest/1',
      sourceUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      collectedAt: '2026-11-18T09:12:00+07:00',
      collector: 'user:thi',
      trigger: { type: 'manual' },
      level: 'full',
      toolVersion: 'h4wk 0.1.0',
      sources: [
        { provider: 'youtube_api', what: 'video.metadata', status: 'ok', startedAt: '2026-11-18T09:12:01+07:00', durationMs: 388, cost: { quotaUnits: 1 } },
        { provider: 'youtube_api', what: 'channel.metadata', status: 'ok', startedAt: '2026-11-18T09:12:02+07:00', durationMs: 305, cost: { quotaUnits: 1 } },
        {
          provider: 'ytdlp',
          what: 'video.transcripts',
          status: 'blocked',
          startedAt: '2026-11-18T09:12:03+07:00',
          durationMs: 1730,
          error: "Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies for the authentication.",
          version: YTDLP,
        },
        { provider: 'supadata', what: 'video.transcripts', status: 'ok', startedAt: '2026-11-18T09:12:05+07:00', durationMs: 2950, cost: { credits: 1 } },
        { provider: 'youtube_api', what: 'video.comments', status: 'ok', startedAt: '2026-11-18T09:12:08+07:00', durationMs: 4120, cost: { quotaUnits: 5 } },
        {
          provider: 'ytdlp',
          what: 'video.thumbnails',
          status: 'blocked',
          startedAt: '2026-11-18T09:12:12+07:00',
          durationMs: 1410,
          error: "Sign in to confirm you're not a bot.",
          version: YTDLP,
        },
        { provider: 'youtube_api', what: 'video.thumbnails', status: 'ok', startedAt: '2026-11-18T09:12:14+07:00', durationMs: 640, cost: { quotaUnits: 0 } },
        {
          provider: 'ytdlp',
          what: 'video.media',
          status: 'blocked',
          startedAt: '2026-11-18T09:12:15+07:00',
          durationMs: 1520,
          error: "Sign in to confirm you're not a bot.",
          version: YTDLP,
        },
        { provider: null, what: 'video.media', status: 'no_source' },
      ],
      files: files('20261118T091200', [
        ['normalized.json', 18911],
        ['sources/youtube_api/video.json', 6188],
        ['sources/youtube_api/channel.json', 3407],
        ['sources/youtube_api/comments.json', 437215],
        ['sources/supadata/transcript.vi.json', 30442],
        ['sources/youtube_api/maxres.jpg', 148213],
      ]),
      previousCapture: '20261117T213000',
    },
  },
  {
    id: '20261116T150500',
    caseId: 'c_demo',
    videoId: 'aBcD1234xyz',
    videoTitle: '',
    manifest: {
      schema: 'h4wk.manifest/1',
      sourceUrl: 'https://www.youtube.com/watch?v=aBcD1234xyz',
      collectedAt: '2026-11-16T15:05:00+07:00',
      collector: 'user:thi',
      trigger: { type: 'manual' },
      level: 'full',
      toolVersion: 'h4wk 0.1.0',
      sources: [
        { provider: 'youtube_api', what: 'video.metadata', status: 'ok', startedAt: '2026-11-16T15:05:01+07:00', durationMs: 455, cost: { quotaUnits: 1 } },
        { provider: 'youtube_api', what: 'channel.metadata', status: 'ok', startedAt: '2026-11-16T15:05:02+07:00', durationMs: 310, cost: { quotaUnits: 1 } },
        { provider: 'ytdlp', what: 'video.transcripts', status: 'ok', startedAt: '2026-11-16T15:05:03+07:00', durationMs: 1980, version: YTDLP },
        { provider: 'youtube_api', what: 'video.comments', status: 'ok', startedAt: '2026-11-16T15:05:05+07:00', durationMs: 1220, cost: { quotaUnits: 2 } },
        { provider: 'ytdlp', what: 'video.thumbnails', status: 'ok', startedAt: '2026-11-16T15:05:07+07:00', durationMs: 870, version: YTDLP },
        { provider: 'ytdlp', what: 'video.media', status: 'ok', startedAt: '2026-11-16T15:05:08+07:00', durationMs: 61500, version: YTDLP },
      ],
      files: files('20261116T150500', [
        ['normalized.json', 14208],
        ['sources/youtube_api/video.json', 5833],
        ['sources/youtube_api/channel.json', 2961],
        ['sources/youtube_api/comments.json', 98412],
        ['sources/ytdlp/aBcD1234xyz.vi-orig.vtt', 41230],
        ['sources/ytdlp/maxres.jpg', 131877],
        ['sources/ytdlp/aBcD1234xyz.mp4', 251090334],
      ]),
      previousCapture: null,
    },
  },
  // Thu tự động từ watchlist; yt-dlp đang bị tắt trong Settings nên ghi `disabled`.
  {
    id: '20261118T080000',
    caseId: 'c_demo',
    videoId: 'qWeRtY98765',
    videoTitle: '',
    manifest: {
      schema: 'h4wk.manifest/1',
      sourceUrl: 'https://www.youtube.com/watch?v=qWeRtY98765',
      collectedAt: '2026-11-18T08:00:00+07:00',
      collector: 'system:watchlist:w_012',
      trigger: { type: 'watchlist', watchItem: 'w_012', event: 'new_video' },
      level: 'full',
      toolVersion: 'h4wk 0.1.0',
      sources: [
        { provider: 'youtube_api', what: 'video.metadata', status: 'ok', startedAt: '2026-11-18T08:00:01+07:00', durationMs: 402, cost: { quotaUnits: 1 } },
        { provider: 'youtube_api', what: 'channel.metadata', status: 'ok', startedAt: '2026-11-18T08:00:02+07:00', durationMs: 287, cost: { quotaUnits: 1 } },
        { provider: 'ytdlp', what: 'video.transcripts', status: 'disabled' },
        { provider: 'supadata', what: 'video.transcripts', status: 'ok', startedAt: '2026-11-18T08:00:03+07:00', durationMs: 3310, cost: { credits: 1 } },
        { provider: 'youtube_api', what: 'video.comments', status: 'ok', startedAt: '2026-11-18T08:00:07+07:00', durationMs: 5260, cost: { quotaUnits: 7 } },
        { provider: 'ytdlp', what: 'video.thumbnails', status: 'disabled' },
        { provider: 'youtube_api', what: 'video.thumbnails', status: 'ok', startedAt: '2026-11-18T08:00:12+07:00', durationMs: 590, cost: { quotaUnits: 0 } },
        { provider: 'ytdlp', what: 'video.media', status: 'disabled' },
        { provider: null, what: 'video.media', status: 'no_source' },
      ],
      files: files('20261118T080000', [
        ['normalized.json', 22704],
        ['sources/youtube_api/video.json', 6544],
        ['sources/youtube_api/channel.json', 3120],
        ['sources/youtube_api/comments.json', 655301],
        ['sources/supadata/transcript.vi.json', 27880],
        ['sources/youtube_api/maxres.jpg', 162009],
      ]),
      previousCapture: null,
    },
  },
  // Mức thu `text`: quota YouTube API hết khi lấy comment nên chuyển sang yt-dlp.
  {
    id: '20261115T103000',
    caseId: 'c_demo',
    videoId: 'zXcV5555aaa',
    videoTitle: '',
    manifest: {
      schema: 'h4wk.manifest/1',
      sourceUrl: 'https://www.youtube.com/watch?v=zXcV5555aaa',
      collectedAt: '2026-11-15T10:30:00+07:00',
      collector: 'user:thi',
      trigger: { type: 'manual' },
      level: 'text',
      toolVersion: 'h4wk 0.1.0',
      sources: [
        { provider: 'youtube_api', what: 'video.metadata', status: 'ok', startedAt: '2026-11-15T10:30:01+07:00', durationMs: 431, cost: { quotaUnits: 1 } },
        { provider: 'youtube_api', what: 'channel.metadata', status: 'ok', startedAt: '2026-11-15T10:30:02+07:00', durationMs: 276, cost: { quotaUnits: 1 } },
        { provider: 'ytdlp', what: 'video.transcripts', status: 'ok', startedAt: '2026-11-15T10:30:03+07:00', durationMs: 2210, version: YTDLP },
        {
          provider: 'youtube_api',
          what: 'video.comments',
          status: 'quota_exceeded',
          startedAt: '2026-11-15T10:30:05+07:00',
          durationMs: 190,
          error: 'quotaExceeded: The request cannot be completed because you have exceeded your quota.',
        },
        { provider: 'ytdlp', what: 'video.comments', status: 'ok', startedAt: '2026-11-15T10:30:06+07:00', durationMs: 9840, version: YTDLP },
        { provider: 'ytdlp', what: 'video.thumbnails', status: 'ok', startedAt: '2026-11-15T10:30:16+07:00', durationMs: 720, version: YTDLP },
      ],
      files: files('20261115T103000', [
        ['normalized.json', 11980],
        ['sources/youtube_api/video.json', 5402],
        ['sources/youtube_api/channel.json', 2840],
        ['sources/ytdlp/comments.json', 87214],
        ['sources/ytdlp/zXcV5555aaa.vi-orig.vtt', 52107],
        ['sources/ytdlp/maxres.jpg', 120554],
      ]),
      previousCapture: null,
    },
  },
  // Mức thu `metadata` của case c_trial.
  {
    id: '20261116T224000',
    caseId: 'c_trial',
    videoId: 'zzZZ9876abc',
    videoTitle: '',
    manifest: {
      schema: 'h4wk.manifest/1',
      sourceUrl: 'https://www.youtube.com/watch?v=zzZZ9876abc',
      collectedAt: '2026-11-16T22:40:00+07:00',
      collector: 'user:thi',
      trigger: { type: 'manual' },
      level: 'metadata',
      toolVersion: 'h4wk 0.1.0',
      sources: [
        { provider: 'youtube_api', what: 'video.metadata', status: 'ok', startedAt: '2026-11-16T22:40:01+07:00', durationMs: 398, cost: { quotaUnits: 1 } },
        { provider: 'youtube_api', what: 'channel.metadata', status: 'ok', startedAt: '2026-11-16T22:40:02+07:00', durationMs: 301, cost: { quotaUnits: 1 } },
        { provider: 'youtube_api', what: 'video.comments', status: 'ok', startedAt: '2026-11-16T22:40:03+07:00', durationMs: 880, cost: { quotaUnits: 1 } },
      ],
      files: files('20261116T224000', [
        ['normalized.json', 4210],
        ['sources/youtube_api/video.json', 4977],
        ['sources/youtube_api/channel.json', 2533],
        ['sources/youtube_api/comments.json', 9120],
      ]),
      previousCapture: null,
    },
  },
]

// Tiêu đề video lấy từ dữ liệu giả có sẵn (mocks/data.ts chưa có danh sách video riêng).
for (const c of captures) {
  c.videoTitle = findings.find((f) => f.videoId === c.videoId)?.videoTitle ?? c.videoId
}

// Kết quả verify cố định để demo: bản thu 20261118T091200 có 1 file bị sửa, 1 file bị xoá, 1 file lạ.
const verifyProblems: Record<string, { fail: string; missing: string; unexpected: [string, number] }> = {
  '20261118T091200': {
    fail: 'sources/youtube_api/comments.json',
    missing: 'sources/supadata/transcript.vi.json',
    unexpected: ['sources/ytdlp/dQw4w9WgXcQ.mp4.part', 1048576],
  },
}

function delay<T>(value: T, ms = 150): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), ms))
}

function find(caseId: string, videoId: string, captureId: string) {
  return captures.find((c) => c.caseId === caseId && c.videoId === videoId && c.id === captureId) ?? null
}

// Danh sách bản thu của một video, mới nhất trước (dùng cho tab Captures của Video detail).
export function listCaptures(caseId: string, videoId: string): Promise<Capture[]> {
  return delay(
    captures.filter((c) => c.caseId === caseId && c.videoId === videoId).sort((a, b) => b.id.localeCompare(a.id)),
  )
}

export function getCapture(caseId: string, videoId: string, captureId: string): Promise<Capture | null> {
  return delay(find(caseId, videoId, captureId))
}

// Giả lập `verify()`: tính lại SHA-256 từng file rồi so với manifest (SPEC 10.2).
export function verifyCapture(caseId: string, videoId: string, captureId: string): Promise<VerifyResult> {
  const capture = find(caseId, videoId, captureId)
  if (!capture) return Promise.reject(new Error('Capture not found'))

  const problems = verifyProblems[captureId]
  const result: VerifyFile[] = Object.entries(capture.manifest.files).map(([path, expected]) => {
    if (path === problems?.missing) return { path, status: 'missing', expected }
    if (path === problems?.fail) {
      return { path, status: 'FAIL', expected, actual: { sha256: fakeSha256(`${path}:edited`), bytes: expected.bytes } }
    }
    return { path, status: 'OK', expected, actual: expected }
  })
  if (problems) {
    const [path, bytes] = problems.unexpected
    result.push({ path, status: 'unexpected', actual: { sha256: fakeSha256(path), bytes } })
  }
  return delay({ captureId, checkedAt: new Date().toISOString(), files: result }, 800)
}
