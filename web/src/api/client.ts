// Gọi API backend qua proxy /api của Vite. Cookie phiên (HttpOnly) được trình duyệt tự gửi kèm.
import type { components } from '@/api/schema'

export type Schemas = components['schemas']

// Lỗi 401: chưa đăng nhập hoặc phiên đã hết hạn.
export class UnauthorizedError extends Error {}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// Lấy thông báo lỗi từ body FastAPI ({"detail": "..."} hoặc danh sách lỗi validate).
async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg: string }) => d.msg).join('; ')
  } catch {
    // body không phải JSON
  }
  return `${res.status} ${res.statusText}`
}

export async function api<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  const res = await fetch(path, {
    method: init?.method ?? 'GET',
    headers: init?.body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: init?.body === undefined ? undefined : JSON.stringify(init.body),
  })
  if (res.status === 401) throw new UnauthorizedError(await errorMessage(res))
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res))
  if (res.status === 204) return undefined as T
  return res.json()
}
