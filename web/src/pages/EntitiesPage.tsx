import { useQuery } from '@tanstack/react-query'
import { ShieldAlertIcon } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import EntityForm from '@/components/entities/EntityForm'
import NewEntityDialog from '@/components/entities/NewEntityDialog'
import RefImageGroup from '@/components/entities/RefImageGroup'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { findings } from '@/mocks/data'
import { listEntities, type Entity } from '@/mocks/entities'

// Nghi vấn của một đối tượng. Dữ liệu giả của nghi vấn ghi tên đối tượng (chưa phải id e_01 như hợp đồng C4),
// nên đếm theo tên; đổi tên đối tượng thì số này về 0 cho tới khi có API thật.
function findingStats(caseId: string, entity: Entity) {
  const list = findings.filter((f) => f.caseId === caseId && f.entity === entity.name)
  const open = list.filter((f) => f.status === 'pending' || f.status === 'needs_info').length
  return { total: list.length, open }
}

export default function EntitiesPage() {
  const { caseId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [creating, setCreating] = useState(false)
  const entities = useQuery({ queryKey: ['entities', caseId], queryFn: () => listEntities(caseId) })

  const all = entities.data ?? []
  // Đối tượng đang chọn nằm trên URL (?entity=e_01) để tải lại trang vẫn giữ; không có thì chọn đối tượng đầu.
  const selected = all.find((e) => e.id === searchParams.get('entity')) ?? all[0] ?? null
  const select = (id: string) => setSearchParams({ entity: id }, { replace: true })
  const refCount = all.reduce((sum, e) => sum + e.refs.length, 0)

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Entities</h1>
        <div className="flex items-center gap-2 text-sm">
          <Badge variant="outline">{all.length} entities</Badge>
          <Badge variant="outline">{refCount} reference images</Badge>
          <Button className="ml-2" onClick={() => setCreating(true)}>
            New entity
          </Button>
        </div>
      </div>

      <Alert>
        <ShieldAlertIcon />
        <AlertTitle>Face images are sensitive personal data</AlertTitle>
        <AlertDescription>
          Under Decree 13/2023/NĐ-CP, face images are sensitive personal data. They are matched only on this machine,
          only against the entities of this case, and are never sent to AI providers. For the demo, the team uses its
          own members' faces as entities.
        </AlertDescription>
      </Alert>

      {entities.isPending && <p className="text-sm text-muted-foreground">Loading entities…</p>}
      {entities.isError && <p className="text-sm text-destructive">Could not load entities.</p>}
      {entities.isSuccess && all.length === 0 && (
        <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          No entities in this case yet. Add the people or organisations you want to protect.
        </p>
      )}

      {selected && (
        <div className="grid grid-cols-[18rem_minmax(0,1fr)] items-start gap-6">
          <ul className="space-y-1">
            {all.map((e) => {
              const stats = findingStats(caseId, e)
              return (
                <li key={e.id}>
                  <button
                    type="button"
                    onClick={() => select(e.id)}
                    aria-current={selected.id === e.id ? 'true' : undefined}
                    className={cn(
                      'w-full rounded-md border p-3 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
                      selected.id === e.id && 'border-primary bg-muted',
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{e.name}</span>
                      <Badge variant={stats.open > 0 ? 'default' : 'secondary'}>{stats.total}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {e.aliases.length} aliases · {e.abbreviations.length} abbr. ·{' '}
                      {e.refs.filter((r) => r.kind === 'face').length} faces ·{' '}
                      {e.refs.filter((r) => r.kind === 'image').length} images
                    </p>
                  </button>
                </li>
              )
            })}
          </ul>

          <EntityDetail key={`${caseId}/${selected.id}`} caseId={caseId} entity={selected} />
        </div>
      )}

      <NewEntityDialog caseId={caseId} open={creating} onOpenChange={setCreating} onCreated={(e) => select(e.id)} />
    </div>
  )
}

function EntityDetail({ caseId, entity }: { caseId: string; entity: Entity }) {
  const stats = findingStats(caseId, entity)
  return (
    <section className="space-y-6 rounded-lg border p-5">
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">{entity.name}</h2>
          <p className="font-mono text-xs text-muted-foreground">{entity.id}</p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">
            {stats.total} findings · {stats.open} open
          </span>
          <Button asChild variant="outline" size="sm">
            <Link to={`/cases/${caseId}/findings`}>View findings</Link>
          </Button>
        </div>
      </div>

      <EntityForm entity={entity} />

      <Separator />

      <div className="space-y-1">
        <h2 className="text-lg font-semibold">Reference images</h2>
        <p className="text-sm text-muted-foreground">
          Used to spot this entity in frames and thumbnails even when nobody says the name.
        </p>
      </div>
      <RefImageGroup
        entity={entity}
        kind="face"
        title="Face images"
        description="Clear photos of the face, for face matching. Processed on this machine only."
      />
      <RefImageGroup
        entity={entity}
        kind="image"
        title="Reused images"
        description="Well-known portraits or logos that often get cropped, edited or pasted into videos."
      />
    </section>
  )
}
