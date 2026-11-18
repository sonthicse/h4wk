import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { validBaseUrl, type DraftProvider } from './draft'

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  existingNames: string[]
  onAdd: (p: DraftProvider) => void
}

// Thêm nhà cung cấp OpenAI-compatible (DeepSeek, OpenRouter…). Model được thêm trong thẻ sau khi tạo.
export default function AddProviderDialog({ open, onOpenChange, existingNames, onAdd }: Props) {
  const [name, setName] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')

  const slug = name.trim()
  const nameError = !slug
    ? null
    : !/^[a-z0-9_-]+$/.test(slug)
      ? 'Use lowercase letters, digits, - or _.'
      : existingNames.includes(slug)
        ? 'A provider with this name already exists.'
        : null
  const urlError = baseUrl.trim() && !validBaseUrl(baseUrl.trim()) ? 'Must start with http:// or https://.' : null
  const canAdd = slug && !nameError && baseUrl.trim() && !urlError

  const close = (next: boolean) => {
    if (!next) {
      setName('')
      setBaseUrl('')
      setApiKey('')
    }
    onOpenChange(next)
  }

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            if (!canAdd) return
            onAdd({
              name: slug,
              type: 'openai_compat',
              baseUrl: baseUrl.trim(),
              models: [],
              apiKeyMasked: null,
              newApiKey: apiKey,
            })
            close(false)
          }}
        >
          <DialogHeader>
            <DialogTitle>Add OpenAI-compatible provider</DialogTitle>
            <DialogDescription>
              Any API that follows the OpenAI chat format. Add its models after creating it, then save.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="new-provider-name">Name</Label>
            <Input
              id="new-provider-name"
              className="font-mono"
              placeholder="openrouter"
              value={name}
              aria-invalid={Boolean(nameError)}
              onChange={(e) => setName(e.target.value)}
            />
            {nameError && <p className="text-xs text-destructive">{nameError}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-provider-url">Base URL</Label>
            <Input
              id="new-provider-url"
              className="font-mono"
              placeholder="https://openrouter.ai/api/v1"
              value={baseUrl}
              aria-invalid={Boolean(urlError)}
              onChange={(e) => setBaseUrl(e.target.value)}
            />
            {urlError && <p className="text-xs text-destructive">{urlError}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-provider-key">API key (optional)</Label>
            <Input
              id="new-provider-key"
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => close(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!canAdd}>
              Add provider
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
