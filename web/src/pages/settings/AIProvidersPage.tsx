import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { PlusIcon } from 'lucide-react'
import { useState } from 'react'
import AddProviderDialog from '@/components/settings/ai/AddProviderDialog'
import { draftErrors, providerChanged, toDraft, toInput, type Draft } from '@/components/settings/ai/draft'
import ProviderCard from '@/components/settings/ai/ProviderCard'
import TaskRoutes from '@/components/settings/ai/TaskRoutes'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AI_TASKS, getAiSettings, saveAiSettings } from '@/mocks/aiProviders'

export default function AIProvidersPage() {
  const queryClient = useQueryClient()
  const settings = useQuery({ queryKey: ['ai-settings'], queryFn: getAiSettings })
  const [draft, setDraft] = useState<Draft | null>(null)
  const [adding, setAdding] = useState(false)
  const [savedAt, setSavedAt] = useState(false)

  const save = useMutation({
    mutationFn: () => saveAiSettings(toInput(draft!)),
    onSuccess: (data) => {
      queryClient.setQueryData(['ai-settings'], data)
      setDraft(toDraft(data))
      setSavedAt(true)
    },
  })

  const saved = settings.data
  // Bản nháp được tạo từ dữ liệu đã lưu ở lần tải đầu tiên (đặt state khi render, theo hướng dẫn của React).
  if (saved && !draft) setDraft(toDraft(saved))

  if (settings.error) return <p className="text-sm text-destructive">Could not load AI settings.</p>
  if (!saved || !draft) return <p className="text-sm text-muted-foreground">Loading…</p>

  const edit = (next: Draft) => {
    setDraft(next)
    setSavedAt(false)
  }
  const savedProvider = (name: string) => saved.providers.find((p) => p.name === name)
  const changedProviders = draft.providers.filter((p) => providerChanged(p, savedProvider(p.name))).length
  const removedProviders = saved.providers.filter((p) => !draft.providers.some((d) => d.name === p.name)).length
  const changedTasks = AI_TASKS.filter((t) => JSON.stringify(draft.tasks[t]) !== JSON.stringify(saved.tasks[t]))
  const dirty = changedProviders + removedProviders + changedTasks.length > 0
  const errors = draftErrors(draft)

  return (
    <div className="space-y-6 pb-16">
      <section className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold">Task routing</h2>
          <p className="text-sm text-muted-foreground">
            Each task tries its models from top to bottom and falls back to the next one on failure.
          </p>
        </div>
        <div className="space-y-3">
          {AI_TASKS.map((t) => (
            <TaskRoutes
              key={t}
              task={t}
              routes={draft.tasks[t]}
              providers={draft.providers}
              changed={changedTasks.includes(t)}
              onChange={(routes) => edit({ ...draft, tasks: { ...draft.tasks, [t]: routes } })}
            />
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Providers</h2>
          <Button variant="outline" onClick={() => setAdding(true)}>
            <PlusIcon />
            Add OpenAI-compatible
          </Button>
        </div>
        <div className="grid grid-cols-1 items-start gap-3 xl:grid-cols-2">
          {draft.providers.map((p) => (
            <ProviderCard
              key={p.name}
              provider={p}
              isNew={!savedProvider(p.name)}
              changed={providerChanged(p, savedProvider(p.name))}
              onChange={(next) => edit({ ...draft, providers: draft.providers.map((x) => (x.name === p.name ? next : x)) })}
              onRemove={() => edit({ ...draft, providers: draft.providers.filter((x) => x.name !== p.name) })}
            />
          ))}
        </div>
      </section>

      <div className="sticky bottom-0 -mx-1 space-y-2 border-t bg-background/95 px-1 py-3 backdrop-blur">
        {errors.length > 0 && (
          <Alert variant="destructive">
            <AlertTitle>Fix before saving</AlertTitle>
            <AlertDescription>
              <ul className="list-inside list-disc">
                {errors.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}
        {save.isError && <p className="text-sm text-destructive">Could not save. Try again.</p>}
        <div className="flex items-center gap-3">
          {dirty ? <Badge variant="outline">Unsaved changes</Badge> : savedAt && <Badge>Saved</Badge>}
          <div className="ml-auto flex gap-2">
            <Button variant="ghost" disabled={!dirty || save.isPending} onClick={() => edit(toDraft(saved))}>
              Discard
            </Button>
            <Button disabled={!dirty || errors.length > 0 || save.isPending} onClick={() => save.mutate()}>
              {save.isPending ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </div>
      </div>

      <AddProviderDialog
        open={adding}
        onOpenChange={setAdding}
        existingNames={draft.providers.map((p) => p.name)}
        onAdd={(p) => edit({ ...draft, providers: [...draft.providers, p] })}
      />
    </div>
  )
}
