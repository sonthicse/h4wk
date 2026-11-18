// API job giả cho trang Collect. Tiến độ được tính theo thời gian trôi qua kể từ lúc tạo job,
// nên poll mỗi 2 giây sẽ thấy job chạy dần. Thay bằng API thật của T12 khi có.

export type CollectLevel = 'metadata' | 'text' | 'full'
export type JobStatus = 'queued' | 'running' | 'done' | 'failed'
export type StepStatus = 'pending' | 'running' | 'done' | 'failed'

export type Job = {
  id: string
  caseId: string
  input: string
  level: CollectLevel
  createdAt: string
  status: JobStatus
  progress: number
  steps: { name: string; status: StepStatus }[]
  error?: string
}

// Các bước con hiện trên giao diện (SPEC 8, màn 2), rút gọn theo mức thu (SPEC 10.7).
const stepsByLevel: Record<CollectLevel, string[]> = {
  metadata: ['collect', 'analyze'],
  text: ['collect', 'OCR/VLM', 'analyze'],
  full: ['collect', 'transcribe', 'frames', 'OCR/VLM', 'match', 'analyze'],
}

const STEP_MS = 4000
const QUEUE_MS = 2000

type StoredJob = Omit<Job, 'status' | 'progress' | 'steps'> & { failAt?: number }

const store: StoredJob[] = [
  {
    id: 'j_002',
    caseId: 'c_demo',
    input: 'https://www.youtube.com/watch?v=aBcD1234xyz',
    level: 'full',
    createdAt: new Date(Date.now() - 60 * 60_000).toISOString(),
  },
  {
    id: 'j_001',
    caseId: 'c_demo',
    input: 'https://www.youtube.com/watch?v=privateVid01',
    level: 'full',
    createdAt: new Date(Date.now() - 2 * 60 * 60_000).toISOString(),
    failAt: 0,
    error: 'yt-dlp: Private video. Sign in if you\'ve been granted access to this video.',
  },
]

function resolve(job: StoredJob): Job {
  const names = stepsByLevel[job.level]
  const elapsed = Date.now() - new Date(job.createdAt).getTime() - QUEUE_MS

  if (elapsed < 0) {
    return { ...job, status: 'queued', progress: 0, steps: names.map((name) => ({ name, status: 'pending' })) }
  }

  const current = Math.floor(elapsed / STEP_MS)
  const steps = names.map((name, i): Job['steps'][number] => {
    if (job.failAt !== undefined && i === job.failAt) return { name, status: 'failed' }
    if (job.failAt !== undefined && i > job.failAt) return { name, status: 'pending' }
    if (i < current) return { name, status: 'done' }
    if (i === current) return { name, status: 'running' }
    return { name, status: 'pending' }
  })

  const doneCount = steps.filter((s) => s.status === 'done').length
  let status: JobStatus = 'running'
  if (steps.some((s) => s.status === 'failed')) status = 'failed'
  else if (doneCount === names.length) status = 'done'

  return {
    ...job,
    status,
    progress: Math.round((doneCount / names.length) * 100),
    steps,
    error: status === 'failed' ? job.error : undefined,
  }
}

function delay<T>(value: T): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), 150))
}

export function listJobs(caseId: string): Promise<Job[]> {
  return delay(store.filter((j) => j.caseId === caseId).map(resolve))
}

export function createJob(caseId: string, input: string, level: CollectLevel): Promise<Job> {
  const job: StoredJob = {
    id: `j_${Date.now()}`,
    caseId,
    input,
    level,
    createdAt: new Date().toISOString(),
  }
  store.unshift(job)
  return delay(resolve(job))
}
