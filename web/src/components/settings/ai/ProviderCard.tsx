import { useMutation } from '@tanstack/react-query'
import { LoaderCircleIcon, Trash2Icon } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { testProvider, type AiModel } from '@/api/settings'
import { hasKey, validBaseUrl, type DraftProvider } from './draft'

const typeLabel: Record<DraftProvider['type'], string> = {
  anthropic: 'Anthropic',
  gemini: 'Gemini',
  openai_compat: 'OpenAI-compatible',
}

type Props = {
  provider: DraftProvider
  isNew: boolean // chưa có trên server
  changed: boolean // khác bản đã lưu
  onChange: (p: DraftProvider) => void
  onRemove: () => void
}

export default function ProviderCard({ provider: p, isNew, changed, onChange, onRemove }: Props) {
  const [editingKey, setEditingKey] = useState(false)
  const [modelName, setModelName] = useState('')
  const [modelCaps, setModelCaps] = useState({ vision: false, structured: false })
  // Test chạy trên cấu hình đã lưu ở server, nên phải Save trước nếu vừa sửa.
  const test = useMutation({ mutationFn: () => testProvider(p.name) })

  const id = `provider-${p.name}`
  const newModel = modelName.trim()
  const modelExists = p.models.some((m) => m.name === newModel)
  const baseUrlInvalid = p.type === 'openai_compat' && !validBaseUrl(p.baseUrl)

  const setModels = (models: AiModel[]) => onChange({ ...p, models })
  const addModel = () => {
    setModels([...p.models, { name: newModel, ...modelCaps }])
    setModelName('')
    setModelCaps({ vision: false, structured: false })
  }

  return (
    <Card size="sm">
      <CardHeader className="flex flex-wrap items-center gap-2">
        <CardTitle className="font-mono">{p.name}</CardTitle>
        <Badge variant="secondary">{typeLabel[p.type]}</Badge>
        {isNew ? <Badge>New</Badge> : changed && <Badge variant="outline">Modified</Badge>}
        <div className="ml-auto flex items-center gap-1">
          <Button
            size="sm"
            variant="outline"
            disabled={changed || test.isPending}
            title={changed ? 'Save changes before testing' : 'Send a small request with the saved settings'}
            onClick={() => test.mutate()}
          >
            {test.isPending && <LoaderCircleIcon className="animate-spin" />}
            {test.isPending ? 'Testing…' : 'Test'}
          </Button>
          {p.type === 'openai_compat' && (
            <Button size="icon-sm" variant="ghost" aria-label={`Remove provider ${p.name}`} onClick={onRemove}>
              <Trash2Icon />
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {(test.data || test.isError) && !test.isPending && (
          <p role="status" className={test.data?.ok ? 'text-sm text-emerald-700 dark:text-emerald-400' : 'text-sm text-destructive'}>
            {test.data?.ok
              ? test.data.latencyMs != null ? `Connected in ${test.data.latencyMs} ms.` : 'Connected.'
              : `Test failed: ${test.data?.message ?? 'could not reach the server.'}`}
          </p>
        )}

        <div className="space-y-1.5">
          <Label htmlFor={`${id}-key`}>API key</Label>
          {p.apiKeyMasked && !editingKey ? (
            <div className="flex items-center gap-2">
              <code id={`${id}-key`} className="flex-1 rounded-md border bg-muted px-3 py-1.5 font-mono text-sm">
                {p.apiKeyMasked}
              </code>
              <Button variant="outline" onClick={() => setEditingKey(true)}>
                Change key
              </Button>
            </div>
          ) : (
            <div className="flex gap-2">
              <Input
                id={`${id}-key`}
                type="password"
                autoComplete="off"
                placeholder={p.apiKeyMasked ? 'Paste the new key' : 'Not set'}
                value={p.newApiKey}
                onChange={(e) => onChange({ ...p, newApiKey: e.target.value })}
              />
              {p.apiKeyMasked && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    onChange({ ...p, newApiKey: '' })
                    setEditingKey(false)
                  }}
                >
                  Cancel
                </Button>
              )}
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            {p.newApiKey.trim()
              ? 'New key will be stored on the server when you save.'
              : hasKey(p)
                ? 'The saved key is never shown again. To change it, enter a new one and save.'
                : 'No key yet. Routes to this provider are skipped.'}
          </p>
        </div>

        {p.type === 'openai_compat' && (
          <div className="space-y-1.5">
            <Label htmlFor={`${id}-url`}>Base URL</Label>
            <Input
              id={`${id}-url`}
              className="font-mono"
              placeholder="https://api.example.com/v1"
              value={p.baseUrl ?? ''}
              aria-invalid={baseUrlInvalid}
              onChange={(e) => onChange({ ...p, baseUrl: e.target.value.trim() || null })}
            />
            {baseUrlInvalid && <p className="text-xs text-destructive">Required, must start with http:// or https://.</p>}
          </div>
        )}

        <div className="space-y-1.5">
          <div className="text-sm font-medium">Models</div>
          <ul className="divide-y rounded-md border text-sm">
            {p.models.map((m, i) => (
              <li key={m.name} className="flex items-center gap-3 px-2 py-1.5">
                <span className="flex-1 truncate font-mono text-xs">{m.name}</span>
                {(['vision', 'structured'] as const).map((cap) => (
                  <label key={cap} className="flex items-center gap-1.5 text-xs">
                    <Checkbox
                      checked={m[cap]}
                      onCheckedChange={(v) => setModels(p.models.map((x, j) => (j === i ? { ...x, [cap]: v === true } : x)))}
                    />
                    {cap}
                  </label>
                ))}
                <Button
                  size="icon-xs"
                  variant="ghost"
                  aria-label={`Remove model ${m.name}`}
                  onClick={() => setModels(p.models.filter((_, j) => j !== i))}
                >
                  <Trash2Icon />
                </Button>
              </li>
            ))}
            {p.models.length === 0 && <li className="px-2 py-1.5 text-xs text-muted-foreground">No models. Add one below.</li>}
          </ul>
          <form
            className="flex items-center gap-3"
            onSubmit={(e) => {
              e.preventDefault()
              if (newModel && !modelExists) addModel()
            }}
          >
            <Input
              className="h-7 flex-1 font-mono text-xs"
              aria-label={`New model name for ${p.name}`}
              placeholder="model name"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
            />
            {(['vision', 'structured'] as const).map((cap) => (
              <label key={cap} className="flex items-center gap-1.5 text-xs">
                <Checkbox
                  checked={modelCaps[cap]}
                  onCheckedChange={(v) => setModelCaps({ ...modelCaps, [cap]: v === true })}
                />
                {cap}
              </label>
            ))}
            <Button type="submit" size="sm" variant="outline" disabled={!newModel || modelExists}>
              Add model
            </Button>
          </form>
          {modelExists && <p className="text-xs text-destructive">This model is already in the list.</p>}
        </div>
      </CardContent>
    </Card>
  )
}
