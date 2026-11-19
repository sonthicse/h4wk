import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Loader2 } from 'lucide-react'
import { useState } from 'react'
import PriorityList from '@/components/settings/sources/PriorityList'
import SourceCard from '@/components/settings/sources/SourceCard'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  caps,
  getSourcesSettings,
  putSourcesSettings,
  setSourceKey,
  sourceLabel,
  type Cap,
  type SourceName,
  type SourcesSettings,
} from '@/api/settings'

// Bản nháp: những gì người dùng đang sửa nhưng chưa Save.
type Draft = {
  enabled: Record<SourceName, boolean>
  priority: Record<Cap, SourceName[]>
  keys: Partial<Record<SourceName, string>>
}

function toDraft(data: SourcesSettings): Draft {
  return {
    enabled: Object.fromEntries(data.sources.map((s) => [s.name, s.enabled])) as Draft['enabled'],
    // Loại dữ liệu mà file cấu hình không ghi thì coi là rỗng.
    priority: Object.fromEntries(caps.map((c) => [c, [...(data.priority[c] ?? [])]])) as Draft['priority'],
    keys: {},
  }
}

function SourcesForm({ data }: { data: SourcesSettings }) {
  const queryClient = useQueryClient()
  const [saved, setSaved] = useState(toDraft(data)) // bản đã lưu, để so sánh
  const [draft, setDraft] = useState(toDraft(data))
  const [justSaved, setJustSaved] = useState(false)

  const save = useMutation({
    mutationFn: async () => {
      const changed = data.sources.filter((s) => draft.enabled[s.name] !== s.enabled)
      await putSourcesSettings({
        sources: Object.fromEntries(changed.map((s) => [s.name, { enabled: draft.enabled[s.name] }])),
        priority: draft.priority,
      })
      // Bật/tắt và thứ tự đã lưu; key mới (nếu có) vẫn là thay đổi chưa lưu.
      setSaved({ ...draft, keys: saved.keys })
      for (const [name, value] of Object.entries(draft.keys)) {
        if (!value) continue
        try {
          await setSourceKey(name as SourceName, value)
        } catch (e) {
          throw new Error(
            `Settings saved, but the ${sourceLabel[name as SourceName]} key was not: ${e instanceof Error ? e.message : e}`,
          )
        }
        // Key đã lưu thì bỏ khỏi bản nháp, để lần Save sau không gửi lại.
        setDraft((d) => ({ ...d, keys: { ...d.keys, [name]: '' } }))
      }
    },
    onSuccess: () => setJustSaved(true),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['sources-settings'] }),
  })

  const hasNewKey = Object.values(draft.keys).some(Boolean)
  const dirty =
    hasNewKey ||
    JSON.stringify(draft.enabled) !== JSON.stringify(saved.enabled) ||
    JSON.stringify(draft.priority) !== JSON.stringify(saved.priority)

  const paused = Object.fromEntries(data.sources.map((s) => [s.name, s.status === 'paused'])) as Record<SourceName, boolean>
  const implemented = Object.fromEntries(data.sources.map((s) => [s.name, s.implemented])) as Record<SourceName, boolean>
  // Danh sách rỗng nghĩa là file cấu hình không ghi; backend tự thử mọi nguồn, chỉ báo khi API báo `uncovered`.
  const emptyCaps = caps.filter((c) =>
    draft.priority[c].length > 0
      ? draft.priority[c].every((n) => !draft.enabled[n] || !implemented[n])
      : data.uncovered.includes(c),
  )

  function edit(next: Partial<Draft>) {
    setJustSaved(false)
    setDraft({ ...draft, ...next })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold">Collection sources</h2>
        <div className="flex items-center gap-3">
          {save.isError && <span className="text-sm text-destructive">{save.error.message}</span>}
          {dirty ? (
            <Badge variant="outline" className="border-amber-500 text-amber-600">
              Unsaved changes
            </Badge>
          ) : justSaved ? (
            <span role="status" className="flex items-center gap-1 text-sm text-muted-foreground">
              <Check className="size-4" /> Saved
            </span>
          ) : null}
          <Button
            variant="outline"
            disabled={!dirty || save.isPending}
            onClick={() => {
              setDraft(saved)
              setJustSaved(false)
            }}
          >
            Discard
          </Button>
          <Button disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
            {save.isPending && <Loader2 className="animate-spin" />}
            Save
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 items-start gap-4">
        {data.sources.map((s) => (
          <SourceCard
            key={s.name}
            source={s}
            enabled={draft.enabled[s.name]}
            onEnabledChange={(v) => edit({ enabled: { ...draft.enabled, [s.name]: v } })}
            newKey={draft.keys[s.name] ?? ''}
            onNewKeyChange={(v) => edit({ keys: { ...draft.keys, [s.name]: v } })}
          />
        ))}
      </div>

      <section className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold">Source priority</h2>
          <p className="text-sm text-muted-foreground">
            For each data type, the first source is tried first. The next one is used only when the one before fails.
            Drag to reorder, or use the arrow buttons.
          </p>
        </div>
        {emptyCaps.length > 0 && (
          <Alert variant="destructive">
            <AlertTitle>{emptyCaps.length === 1 ? 'A data type has' : `${emptyCaps.length} data types have`} no enabled source</AlertTitle>
            <AlertDescription>{emptyCaps.join(', ')}</AlertDescription>
          </Alert>
        )}
        <div className="grid grid-cols-2 gap-3">
          {caps.map((cap) => (
            <PriorityList
              key={cap}
              cap={cap}
              order={draft.priority[cap]}
              enabled={draft.enabled}
              paused={paused}
              changed={JSON.stringify(draft.priority[cap]) !== JSON.stringify(saved.priority[cap])}
              onChange={(order) => edit({ priority: { ...draft.priority, [cap]: order } })}
            />
          ))}
        </div>
      </section>
    </div>
  )
}

export default function SourcesPage() {
  const settings = useQuery({ queryKey: ['sources-settings'], queryFn: getSourcesSettings })

  if (settings.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load sources</AlertTitle>
        <AlertDescription>
          <Button variant="outline" size="sm" onClick={() => settings.refetch()}>
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    )
  }
  if (!settings.data) return <Skeleton className="h-96 w-full" />
  // Form giữ bản nháp riêng nên khi Resume làm dữ liệu tải lại, phần đang sửa không bị mất.
  return <SourcesForm data={settings.data} />
}
