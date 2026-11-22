
import type { components } from '@/api/schema'

export type Schemas = components['schemas']

export class UnauthorizedError extends Error {}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg: string }) => d.msg).join('; ')
  } catch {

  }
  return `${res.status} ${res.statusText}`
}

export async function api<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  const body = init?.body
  const raw = body instanceof Blob
  const res = await fetch(path, {
    method: init?.method ?? 'GET',
    headers:
      body === undefined ? undefined : { 'Content-Type': raw ? body.type || 'application/octet-stream' : 'application/json' },
    body: body === undefined ? undefined : raw ? body : JSON.stringify(body),
  })
  if (res.status === 401) throw new UnauthorizedError(await errorMessage(res))
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res))
  if (res.status === 204) return undefined as T
  return res.json()
}
