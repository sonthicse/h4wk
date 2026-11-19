import { api, type Schemas } from '@/api/client'

export type Entity = Schemas['Entity']

export function listEntities(): Promise<Entity[]> {
  return api('/api/entities')
}

export function createEntity(name: string, aliases: string[] = [], abbreviations: string[] = []): Promise<Entity> {
  return api('/api/entities', { method: 'POST', body: { name, aliases, abbreviations } })
}
