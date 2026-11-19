import { ArrowDownIcon, ArrowUpIcon, PlusIcon, Trash2Icon, TriangleAlertIcon } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { AiRoute, AiTask } from '@/api/settings'
import { modelAllowed, routeProblem, type DraftProvider } from './draft'

const taskInfo: Record<AiTask, string> = {
  'analysis.classify': 'Classifies transcript and OCR segments into findings.',
  'analysis.classify_comment': 'Classifies comments under watched videos.',
  'media.vision': 'Describes video frames. Only models with vision can be used.',
}

type Props = {
  task: AiTask
  routes: AiRoute[]
  providers: DraftProvider[]
  changed: boolean
  onChange: (routes: AiRoute[]) => void
}

// Một tác vụ AI: danh sách (provider, model) theo thứ tự ưu tiên; dòng đầu được thử trước.
export default function TaskRoutes({ task, routes, providers, changed, onChange }: Props) {
  const problems = routes.map((r) => routeProblem(task, r, providers))
  const usable = problems.some((p) => p === null)

  const update = (i: number, route: AiRoute) => onChange(routes.map((r, j) => (j === i ? route : r)))
  const move = (i: number, by: number) => {
    const next = [...routes]
    ;[next[i], next[i + by]] = [next[i + by], next[i]]
    onChange(next)
  }
  // Model đầu tiên của nhà cung cấp mà tác vụ này cho phép.
  const firstModel = (providerName: string) =>
    providers.find((p) => p.name === providerName)?.models.find((m) => modelAllowed(task, m))?.name ?? ''
  const addRoute = () => {
    const first = providers.find((p) => firstModel(p.name))
    if (first) onChange([...routes, { provider: first.name, model: firstModel(first.name) }])
  }

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 font-mono">
          {task}
          {changed && <Badge variant="outline">Modified</Badge>}
        </CardTitle>
        <CardDescription>{taskInfo[task]}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {!usable && (
          <Alert variant="destructive">
            <TriangleAlertIcon />
            <AlertTitle>No usable model</AlertTitle>
            <AlertDescription>
              {routes.length === 0
                ? 'This task has no model assigned.'
                : 'Every model below is unavailable, so this task will fail. Set an API key or pick another model.'}
            </AlertDescription>
          </Alert>
        )}

        <ol className="space-y-2">
          {routes.map((r, i) => {
            const provider = providers.find((p) => p.name === r.provider)
            const problem = problems[i]
            return (
              <li key={i} className="flex flex-wrap items-center gap-2">
                <span className="w-6 text-right text-sm text-muted-foreground">{i + 1}.</span>
                <Select
                  value={r.provider}
                  onValueChange={(name) => update(i, { provider: name, model: firstModel(name) })}
                >
                  <SelectTrigger className="w-44" aria-label={`${task} provider ${i + 1}`}>
                    <SelectValue placeholder="Provider" />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.map((p) => (
                      <SelectItem key={p.name} value={p.name}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={r.model} onValueChange={(model) => update(i, { ...r, model })}>
                  <SelectTrigger className="w-60 font-mono text-xs" aria-label={`${task} model ${i + 1}`}>
                    <SelectValue placeholder="Model" />
                  </SelectTrigger>
                  <SelectContent>
                    {(provider?.models ?? []).map((m) => (
                      <SelectItem key={m.name} value={m.name} disabled={!modelAllowed(task, m)}>
                        <span className="font-mono text-xs">{m.name}</span>
                        {!modelAllowed(task, m) && <span className="text-xs text-muted-foreground">no vision</span>}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {problem && (
                  <span className={problem.blocking ? 'text-xs text-destructive' : 'text-xs text-amber-700 dark:text-amber-400'}>
                    {problem.reason}
                  </span>
                )}
                <div className="ml-auto flex items-center">
                  <Button size="icon-sm" variant="ghost" aria-label={`Move ${task} route ${i + 1} up`} disabled={i === 0} onClick={() => move(i, -1)}>
                    <ArrowUpIcon />
                  </Button>
                  <Button size="icon-sm" variant="ghost" aria-label={`Move ${task} route ${i + 1} down`} disabled={i === routes.length - 1} onClick={() => move(i, 1)}>
                    <ArrowDownIcon />
                  </Button>
                  <Button size="icon-sm" variant="ghost" aria-label={`Remove ${task} route ${i + 1}`} onClick={() => onChange(routes.filter((_, j) => j !== i))}>
                    <Trash2Icon />
                  </Button>
                </div>
              </li>
            )
          })}
        </ol>
        <Button size="sm" variant="outline" onClick={addRoute}>
          <PlusIcon />
          Add fallback
        </Button>
      </CardContent>
    </Card>
  )
}
