// Kiểu viết tay tạm thời; sẽ thay bằng kiểu sinh từ OpenAPI (`npm run gen:api`) ở task sau.
export type Health = { status: string }

export async function getHealth(): Promise<Health> {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error(`GET /api/health failed: ${res.status}`)
  return res.json()
}
