import { api, type Schemas } from '@/api/client'

export type Me = Schemas['Me']

export function login(username: string, password: string): Promise<void> {
  return api('/api/auth/login', { method: 'POST', body: { username, password } })
}

export function logout(): Promise<void> {
  return api('/api/auth/logout', { method: 'POST' })
}

export function getMe(): Promise<Me> {
  return api('/api/auth/me')
}
