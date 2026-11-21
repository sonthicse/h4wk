import { useQuery } from '@tanstack/react-query'
import { ShieldAlertIcon } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { listEntities, type Entity } from '@/api/entities'
import EntityForm from '@/components/entities/EntityForm'
import NewEntityDialog from '@/components/entities/NewEntityDialog'
import RefImageGroup from '@/components/entities/RefImageGroup'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

// "1 entity" / "2 entities".
function plural(n: number, word: string) {
  return n === 1 ? `${n} ${word}` : `${n} ${word === 'entity' ? 'entities' : word + 's'}`
}

export default function EntitiesPage() {
  const [creating, setCreating] = useState(false)
  const entities = useQuery({ queryKey: ['entities'], queryFn: listEntities })
  const all = entities.data ?? []

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-semibold">Entities</h1>
        <Badge variant="outline">{plural(all.length, 'entity')}</Badge>
        <Button className="ml-auto" onClick={() => setCreating(true)}>
          New entity
        </Button>
      </div>

      <Alert>
        <ShieldAlertIcon />
        <AlertTitle>Face images are sensitive personal data</AlertTitle>
        <AlertDescription>
          Faces are matched only against declared entities, on this machine. Demo uses public portraits of a public
          figure (Wikimedia Commons).
        </AlertDescription>
      </Alert>

      {entities.isPending && <p className="text-sm text-muted-foreground">Loading entities…</p>}
      {entities.error && <p className="text-sm text-destructive">Could not load entities: {entities.error.message}</p>}
      {entities.isSuccess && all.length === 0 && (
        <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          No entities yet. Add the people or organisations you want to protect.
        </p>
      )}

      {all.map((e) => (
        <EntityCard key={e.id} entity={e} />
      ))}

      <NewEntityDialog open={creating} onOpenChange={setCreating} onCreated={() => setCreating(false)} />
    </div>
  )
}

// Một thẻ cho mỗi đối tượng: thông tin sửa được, rồi hai nhóm ảnh mẫu đặt cạnh nhau.
function EntityCard({ entity }: { entity: Entity }) {
  return (
    <section className="space-y-4 rounded-xl border p-5">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold">{entity.name}</h2>
        <span className="font-mono text-xs text-muted-foreground">{entity.id}</span>
        <Link to="/findings" className="ml-auto text-sm hover:text-muted-foreground">
          View findings
        </Link>
      </div>

      <EntityForm entity={entity} />

      <Separator />

      <h3 className="font-semibold">Reference images</h3>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <RefImageGroup entity={entity} kind="face" title="Face" />
        <RefImageGroup entity={entity} kind="image" title="Image" />
      </div>
    </section>
  )
}
