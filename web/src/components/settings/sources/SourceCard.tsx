import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CircleCheck, CircleX } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { LoaderCircleIcon } from '@/components/animate-ui/icons/loader-circle'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Switch } from '@/components/ui/switch'
import { formatVnDateTime } from '@/lib/format'
import { resumeSource, sourceLabel, testSource, type SourceInfo } from '@/api/settings'

type Props = {
  source: SourceInfo
  enabled: boolean
  onEnabledChange: (value: boolean) => void
  // Key mới đang nhập dở ('' nếu chưa nhập); chỉ gửi đi khi bấm Save.
  newKey: string
  onNewKeyChange: (value: string) => void
}

// Một nguồn thu: bật/tắt, key, trạng thái, quota và nút Test connection.
export default function SourceCard({ source, enabled, onEnabledChange, newKey, onNewKeyChange }: Props) {
  const queryClient = useQueryClient()
  const [editingKey, setEditingKey] = useState(false)
  const name = sourceLabel[source.name]

  // API không trả thời điểm test nên lấy giờ máy lúc nhận kết quả.
  const test = useMutation({
    mutationFn: async () => ({ result: await testSource(source.name), testedAt: new Date().toISOString() }),
  })
  const resume = useMutation({
    mutationFn: () => resumeSource(source.name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sources-settings'] }),
  })

  const usage = source.usage
  const unit = usage?.period === 'day' ? 'units' : 'credits'
  const percent = usage ? Math.min(100, Math.round((usage.used / usage.limit) * 100)) : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {name}
          {!enabled ? (
            <Badge variant="outline">disabled</Badge>
          ) : source.status === 'paused' ? (
            <Badge variant="destructive">paused</Badge>
          ) : (
            <Badge variant="secondary">active</Badge>
          )}
        </CardTitle>
        <CardAction>
          <Switch checked={enabled} onCheckedChange={onEnabledChange} aria-label={`Enable ${name}`} />
        </CardAction>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        {source.status === 'paused' && (
          <div className="space-y-2 rounded-md border border-destructive/40 p-3">
            <p>
              Paused after {source.consecutive_failures} failures in a row
              {source.paused_until && <> until {formatVnDateTime(source.paused_until)}</>}.
            </p>
            {source.last_error && <p className="font-mono text-xs text-muted-foreground">{source.last_error}</p>}
            <Button size="sm" variant="outline" disabled={resume.isPending} onClick={() => resume.mutate()}>
              {resume.isPending && <LoaderCircleIcon animate />}
              {resume.isPending ? 'Resuming…' : 'Resume now'}
            </Button>
            {resume.isError && <p className="text-xs text-destructive">{resume.error.message}</p>}
          </div>
        )}

        {source.needs_key ? (
          <div className="space-y-1.5">
            <label htmlFor={`key-${source.name}`} className="font-medium">
              API key
            </label>
            {editingKey ? (
              <div className="flex gap-2">
                <Input
                  id={`key-${source.name}`}
                  type="password"
                  autoComplete="off"
                  placeholder="Paste the new key"
                  value={newKey}
                  onChange={(e) => onNewKeyChange(e.target.value)}
                />
                <Button
                  variant="ghost"
                  onClick={() => {
                    onNewKeyChange('')
                    setEditingKey(false)
                  }}
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <code id={`key-${source.name}`} className="flex-1 rounded-md border bg-muted px-3 py-1.5 font-mono">
                  {source.key?.masked ?? 'Not set'}
                </code>
                <Button variant="outline" onClick={() => setEditingKey(true)}>
                  {source.key?.masked ? 'Change key' : 'Set key'}
                </Button>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              The saved key is never shown again. To change it, enter a new one and save.
            </p>
          </div>
        ) : (
          <p className="text-muted-foreground">No API key needed.</p>
        )}

        {usage && (
          <div className="space-y-1.5">
            <div className="flex justify-between">
              <span className="font-medium">{usage.period === 'day' ? 'Quota today' : 'Credits this month'}</span>
              <span className="tabular-nums">
                {usage.used.toLocaleString('en-US')} / {usage.limit.toLocaleString('en-US')} {unit}
              </span>
            </div>
            <Progress value={percent} aria-label={`${name} usage`} />
            {usage.resets_at && (
              <p className="text-xs text-muted-foreground">Resets {formatVnDateTime(usage.resets_at)}</p>
            )}
          </div>
        )}

        <div className="space-y-2 border-t pt-3">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" disabled={test.isPending} onClick={() => test.mutate()}>
              {test.isPending && <LoaderCircleIcon animate />}
              {test.isPending ? 'Testing…' : 'Test connection'}
            </Button>
            {newKey && <span className="text-xs text-muted-foreground">Tests the saved key, not the new one. Save first.</span>}
          </div>
          {test.isError && <p className="text-xs text-destructive">{test.error.message}</p>}
          {test.data && (
            <p
              role="status"
              className={`flex items-start gap-1.5 text-xs ${test.data.result.ok ? 'text-foreground' : 'text-destructive'}`}
            >
              {test.data.result.ok ? <CircleCheck className="mt-px size-3.5 shrink-0" /> : <CircleX className="mt-px size-3.5 shrink-0" />}
              <span>
                {test.data.result.detail}
                {test.data.result.latency_ms != null && <> ({test.data.result.latency_ms} ms)</>}{' '}
                <span className="text-muted-foreground">({formatVnDateTime(test.data.testedAt)})</span>
              </span>
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
