import { useQuery } from '@tanstack/react-query'
import { ShieldAlertIcon } from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { listEntities, type Entity } from '@/api/entities'
import EntityForm from '@/components/entities/EntityForm'
import { listFindings } from '@/api/findings'
import NewEntityDialog from '@/components/entities/NewEntityDialog'
import RefImageGroup from '@/components/entities/RefImageGroup'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import type { Finding } from '@/api/findings'

// Số nghi vấn của một đối tượng (nghi vấn ghi id đối tượng, ví dụ e_01). Chưa có API rà soát (T25)
// nên chưa biết nghi vấn nào còn mở; chỉ đếm tổng.
function findingCount(findings: Finding[], entity: Entity) {
  return findings.filter((f) => f.entity === entity.id).length
}

// "1 image" / "2 images"; từ đặc biệt: entity → entities, alias → aliases.
function plural(n: number, word: string) {
  if (n === 1) return `${n} ${word}`
  return `${n} ${word === 'entity' ? 'entities' : word === 'alias' ? 'aliases' : word + 's'}`
}

export default function EntitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [creating, setCreating] = useState(false)
  const entities = useQuery({ queryKey: ['entities'], queryFn: listEntities })
  const findings = useQuery({ queryKey: ['findings'], queryFn: listFindings }).data ?? []

  const all = entities.data ?? []
  // Đối tượng đang chọn nằm trên URL (?entity=e_01) để tải lại trang vẫn giữ; không có thì chọn đối tượng đầu.
  const selected = all.find((e) => e.id === searchParams.get('entity')) ?? all[0] ?? null
  const select = (id: string) => setSearchParams({ entity: id }, { replace: true })
  const refCount = all.reduce((sum, e) => sum + e.ref_counts.face + e.ref_counts.image, 0)

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Entities</h1>
        <div className="flex items-center gap-2 text-sm">
          <Badge variant="outline">{plural(all.length, 'entity')}</Badge>
          <Badge variant="outline">{plural(refCount, 'reference image')}</Badge>
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
          only against the entities listed here, and are never sent to AI providers. For the demo, the team uses its
          own members' faces as entities.
        </AlertDescription>
      </Alert>

      {entities.isPending && <p className="text-sm text-muted-foreground">Loading entities…</p>}
      {entities.error && <p className="text-sm text-destructive">Could not load entities: {entities.error.message}</p>}
      {entities.isSuccess && all.length === 0 && (
        <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          No entities yet. Add the people or organisations you want to protect.
        </p>
      )}

      {selected && (
        <div className="grid grid-cols-[18rem_minmax(0,1fr)] items-start gap-6">
          <ul className="space-y-1">
            {all.map((e) => {
              const total = findingCount(findings, e)
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
                      <Badge variant={total > 0 ? 'default' : 'secondary'}>{plural(total, 'finding')}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {plural(e.aliases.length, 'alias')} · {e.abbreviations.length} abbr. ·{' '}
                      {plural(e.ref_counts.face, 'face')} ·{' '}
                      {plural(e.ref_counts.image, 'image')}
                    </p>
                  </button>
                </li>
              )
            })}
          </ul>

          <EntityDetail key={selected.id} entity={selected} findingTotal={findingCount(findings, selected)} />
        </div>
      )}

      <NewEntityDialog open={creating} onOpenChange={setCreating} onCreated={(e) => select(e.id)} />
    </div>
  )
}

function EntityDetail({ entity, findingTotal }: { entity: Entity; findingTotal: number }) {
  return (
    <section className="space-y-6 rounded-lg border p-5">
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">{entity.name}</h2>
          <p className="font-mono text-xs text-muted-foreground">{entity.id}</p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">
            {plural(findingTotal, 'finding')}
          </span>
          <Button asChild variant="outline" size="sm">
            <Link to="/findings">View findings</Link>
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
