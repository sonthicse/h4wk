import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckIcon, TriangleAlertIcon } from 'lucide-react'
import { useState } from 'react'
import { deleteJevKey, getJevSettings, getJevUsage, setJevKey, testJev, type JevUsagePeriod } from '@/api/settings'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatVnDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'

const periods: { value: JevUsagePeriod; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: '7d', label: '7 days' },
  { value: '30d', label: '30 days' },
]

const sourceLabel: Record<string, string> = {
  metadata: 'Title and description',
  speech: 'Speech segments',
  comment: 'Comments',
  visual: 'Keyframes (images + OCR)',
  ocr: 'OCR text',
  thumbnail: 'Thumbnails (image + OCR)',
  connection_test: 'Connection test',
}

const num = (n: number) => n.toLocaleString('en-US')
// Null nghĩa là TypeSafe không báo số; khác với 0.
const tokens = (n: number | null) => (n === null ? 'Not reported' : num(n))

function KeyCard() {
  const queryClient = useQueryClient()
  const jev = useQuery({ queryKey: ['jev-settings'], queryFn: getJevSettings })
  const [value, setValue] = useState('')
  const [editing, setEditing] = useState(false)
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['jev-settings'] })

  const save = useMutation({
    mutationFn: () => setJevKey(value.trim()),
    onSuccess: () => {
      setValue('')
      setEditing(false)
      test.reset()
      return refresh()
    },
  })
  const remove = useMutation({
    mutationFn: deleteJevKey,
    onSuccess: () => {
      test.reset()
      return refresh()
    },
  })
  const test = useMutation({
    mutationFn: testJev,
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['jev-usage'] }),
  })
  const busy = save.isPending || remove.isPending
  const key = jev.data?.key
  const error = save.error ?? remove.error

  const cancel = () => {
    setValue('')
    setEditing(false)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>API key</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {jev.error && <p className="text-destructive">Could not load Jev settings.</p>}
        {key && !key.set && (
          <Alert>
            <TriangleAlertIcon />
            <AlertTitle>Jev is off</AlertTitle>
            <AlertDescription>Add a TypeSafe API key to analyse speech, comments, titles and images.</AlertDescription>
          </Alert>
        )}
        {/* Cùng cách nhập key như thẻ nguồn ở Settings → Sources. */}
        <div className="space-y-1.5">
          <label htmlFor="jev-key" className="font-medium">
            TypeSafe API key
          </label>
          {editing ? (
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                if (value.trim()) save.mutate()
              }}
            >
              <Input
                id="jev-key"
                type="password"
                autoComplete="off"
                autoFocus
                placeholder="Paste the new key"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
              <Button type="submit" disabled={busy || !value.trim()}>
                {save.isPending ? 'Saving…' : 'Save key'}
              </Button>
              <Button type="button" variant="ghost" onClick={cancel}>
                Cancel
              </Button>
            </form>
          ) : (
            <div className="flex items-center gap-2">
              <code id="jev-key" className="flex-1 rounded-md border bg-muted px-3 py-1.5 font-mono">
                {key?.masked ?? 'Not set'}
              </code>
              <Button variant="outline" onClick={() => setEditing(true)}>
                {key?.set ? 'Change key' : 'Set key'}
              </Button>
              {key?.set && key.origin === 'settings' && (
                <Button variant="outline" disabled={busy} onClick={() => remove.mutate()}>
                  Remove
                </Button>
              )}
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            The saved key is never shown again. To change it, enter a new one and save.
          </p>
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error.message}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3 border-t pt-4">
          <Button variant="outline" disabled={!key?.set || test.isPending} onClick={() => test.mutate()}>
            {test.isPending ? 'Testing…' : 'Test connection'}
          </Button>
          {test.data?.ok && (
            <span role="status" className="flex items-center gap-1.5 text-sm text-green-700 dark:text-green-400">
              <CheckIcon className="size-4" />
              Connected{test.data.model ? ` · ${test.data.model}` : ''}
              {test.data.latency_ms != null ? ` · ${test.data.latency_ms} ms` : ''}
            </span>
          )}
          {test.data && !test.data.ok && (
            <span role="alert" className="text-sm text-destructive">
              {test.data.error ?? 'Connection failed'}
            </span>
          )}
          {test.isError && (
            <span role="alert" className="text-sm text-destructive">
              {test.error.message}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg bg-muted/50 px-3.5 py-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={cn('text-xl font-semibold', value === 'Not reported' && 'text-base font-normal text-muted-foreground')}>{value}</span>
      {note && <span className="text-xs text-muted-foreground">{note}</span>}
    </div>
  )
}

function UsageCard() {
  const [period, setPeriod] = useState<JevUsagePeriod>('7d')
  const usage = useQuery({ queryKey: ['jev-usage', period], queryFn: () => getJevUsage(period) })
  const u = usage.data

  return (
    <Card aria-labelledby="usage-title">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-3">
          <CardTitle id="usage-title">Usage</CardTitle>
          <div role="group" aria-label="Period" className="ml-auto flex overflow-hidden rounded-lg border">
            {periods.map((p) => (
              <button
                key={p.value}
                type="button"
                aria-pressed={period === p.value}
                onClick={() => setPeriod(p.value)}
                className={cn('h-9 border-l px-3 text-sm first:border-l-0', period === p.value ? 'bg-primary text-primary-foreground' : 'hover:bg-muted')}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
        <p className="text-sm text-muted-foreground">Token counts reported by TypeSafe. Totals include only reported counts.</p>
      </CardHeader>
      <CardContent className="space-y-5">
        {usage.error && <p className="text-sm text-destructive">Could not load Jev usage.</p>}
        {!u && !usage.error && <p className="text-sm text-muted-foreground">Loading…</p>}
        {u && (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
              <Stat label="Requests" value={num(u.requests)} />
              <Stat label="With images" value={num(u.image_requests)} note="keyframes + thumbnails" />
              <Stat label="Input tokens" value={tokens(u.input_tokens)} />
              <Stat label="Output tokens" value={tokens(u.output_tokens)} />
              <Stat
                label="Findings kept"
                value={num(u.kept)}
                note={u.requests > 0 ? `${Math.round((u.kept / u.requests) * 100)}% of requests` : undefined}
              />
              <Stat label="Failed" value={num(u.errors)} note={`429 retried: ${num(u.retries_429)}`} />
            </div>
            <span className="block text-xs text-muted-foreground">By source</span>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead className="text-right">Requests</TableHead>
                  <TableHead className="text-right">Input tokens</TableHead>
                  <TableHead className="text-right">Output tokens</TableHead>
                  <TableHead className="text-right">Kept</TableHead>
                  <TableHead className="text-right">Failed</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {u.by_source.map((r) => (
                  <TableRow key={r.source}>
                    <TableCell>{sourceLabel[r.source] ?? r.source}</TableCell>
                    <TableCell className="text-right font-mono">{num(r.requests)}</TableCell>
                    <TableCell className="text-right font-mono">{tokens(r.input_tokens)}</TableCell>
                    <TableCell className="text-right font-mono">{tokens(r.output_tokens)}</TableCell>
                    <TableCell className="text-right font-mono">{num(r.kept)}</TableCell>
                    <TableCell className="text-right font-mono">{num(r.errors)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="space-y-1.5">
              <span className="text-xs text-muted-foreground">Last errors</span>
              {u.recent_errors.length === 0 ? (
                <p className="text-sm text-muted-foreground">No errors in this period.</p>
              ) : (
                u.recent_errors.map((e, i) => (
                  <p key={i} className="font-mono text-xs text-destructive">
                    {e.status} · {sourceLabel[e.source] ?? e.source} · {e.video_id ?? 'no video'} · {formatVnDateTime(e.at)}
                  </p>
                ))
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

export default function JevPage() {
  return (
    <div className="space-y-5">
      <KeyCard />
      <UsageCard />
    </div>
  )
}
