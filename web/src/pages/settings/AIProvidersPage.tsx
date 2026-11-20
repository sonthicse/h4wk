import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimateIcon } from '@animate-ui/react/icons'
import { CheckIcon } from '@/components/animate-ui/icons/check'
import { LoaderCircleIcon } from '@/components/animate-ui/icons/loader-circle'
import { PlusIcon } from '@/components/animate-ui/icons/plus'
import { useState } from 'react'
import AddProviderDialog from '@/components/settings/ai/AddProviderDialog'
import { draftErrors, providerChanged, toDraft, toInput, type Draft } from '@/components/settings/ai/draft'
import JevCard from '@/components/settings/ai/JevCard'
import ProviderCard from '@/components/settings/ai/ProviderCard'
import TaskRoutes from '@/components/settings/ai/TaskRoutes'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AI_TASKS, getAiSettings, saveAiSettings } from '@/api/settings'

export default function AIProvidersPage() {
  const queryClient = useQueryClient()
  const settings = useQuery({ queryKey: ['ai-settings'], queryFn: getAiSettings })
  const [draft, setDraft] = useState<Draft | null>(null)
  const [adding, setAdding] = useState(false)
  const [savedAt, setSavedAt] = useState(false)

  const save = useMutation({
    mutationFn: () => saveAiSettings(toInput(draft!)),
    // Lưu nửa chừng vẫn làm dữ liệu đã lưu đổi, nên tải lại cả khi lỗi.
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['ai-settings'] }),
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
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-lg font-semibold">AI providers</h2>
        <div className="flex flex-wrap items-center gap-3">
          {dirty ? (
            <Badge variant="outline" className="border-amber-500 text-amber-600">
              Unsaved changes
            </Badge>
          ) : savedAt ? (
            <span role="status" className="flex items-center gap-1 text-sm text-muted-foreground">
              <CheckIcon className="size-4" animate /> Saved
            </span>
          ) : null}
          <Button variant="outline" disabled={!dirty || save.isPending} onClick={() => edit(toDraft(saved))}>
            Discard
          </Button>
          <Button disabled={!dirty || errors.length > 0 || save.isPending} onClick={() => save.mutate()}>
            {save.isPending && <LoaderCircleIcon animate />}
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>

      {/* Lưu thất bại: hiện detail của API, bản nháp giữ nguyên để sửa rồi Save lại. */}
      {save.isError && (
        <Alert variant="destructive" role="alert">
          <AlertTitle>Could not save</AlertTitle>
          <AlertDescription>{save.error.message}</AlertDescription>
        </Alert>
      )}

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

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Providers</h2>
          <AnimateIcon animateOnHover asChild>
            <Button variant="outline" onClick={() => setAdding(true)}>
              <PlusIcon />
              Add OpenAI-compatible
            </Button>
          </AnimateIcon>
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

      <JevCard />

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

      <AddProviderDialog
        open={adding}
        onOpenChange={setAdding}
        existingNames={draft.providers.map((p) => p.name)}
        onAdd={(p) => edit({ ...draft, providers: [...draft.providers, p] })}
      />
    </div>
  )
}
