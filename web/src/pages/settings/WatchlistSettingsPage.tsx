import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getWatchlistSettings, putWatchlistSettings, type WatchlistSettings } from '@/api/settings'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'

type Field = 'check_interval_min' | 'initial_videos' | 'threads_per_channel'

const fields: { key: Field; label: string; hint: string; min: number; max?: number }[] = [
  {
    key: 'threads_per_channel',
    label: 'Threads per channel',
    hint: 'Each channel processes up to this many videos at once. Channels run in parallel, so a busy channel never blocks another. GPU steps (speech to text, OCR, image matching) still share one GPU.',
    min: 1,
    max: 8,
  },
  {
    key: 'initial_videos',
    label: 'Videos collected when a channel is added',
    hint: 'The newest videos of a new channel that are collected and processed right away.',
    min: 0,
  },
  {
    key: 'check_interval_min',
    label: 'Check interval (minutes)',
    hint: 'How often enabled channels are checked by RSS for new videos.',
    min: 1,
  },
]

function Form({ data }: { data: WatchlistSettings }) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<Record<Field, string>>({
    check_interval_min: String(data.check_interval_min),
    initial_videos: String(data.initial_videos),
    threads_per_channel: String(data.threads_per_channel),
  })
  const changed = fields.some((f) => draft[f.key] !== String(data[f.key]))

  const save = useMutation({
    mutationFn: () => putWatchlistSettings(Object.fromEntries(fields.map((f) => [f.key, Number(draft[f.key])]))),
    onSuccess: (saved) => queryClient.setQueryData(['watchlist-settings'], saved),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Watchlist processing</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-5 text-sm"
          onSubmit={(e) => {
            e.preventDefault()
            save.mutate()
          }}
        >
          {fields.map((f) => (
            <div key={f.key} className="space-y-1.5">
              <label htmlFor={f.key} className="font-medium">
                {f.label}
              </label>
              <Input
                id={f.key}
                type="number"
                inputMode="numeric"
                min={f.min}
                max={f.max}
                className="w-32"
                value={draft[f.key]}
                onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">{f.hint}</p>
            </div>
          ))}
          <p className="text-xs text-muted-foreground">
            The worker needs {data.worker_threads} threads for these settings ({data.threads_per_channel} per enabled
            channel, plus 2). It sizes itself when it starts, so restart it after adding many channels or raising the
            threads per channel.
          </p>
          <div className="flex items-center gap-3 border-t pt-4">
            <Button type="submit" disabled={!changed || save.isPending}>
              {save.isPending ? 'Saving…' : 'Save'}
            </Button>
            {save.isError && (
              <span role="alert" className="text-destructive">
                {save.error.message}
              </span>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

// Settings → Watchlist: số luồng mỗi kênh, số video khi thêm kênh, chu kỳ kiểm tra.
export default function WatchlistSettingsPage() {
  const q = useQuery({ queryKey: ['watchlist-settings'], queryFn: getWatchlistSettings })
  if (q.error) return <p className="text-sm text-destructive">Could not load watchlist settings.</p>
  if (!q.data) return <Skeleton className="h-64 w-full" />
  // key: tải lại dữ liệu sau khi lưu thì form bắt đầu từ giá trị mới.
  return <Form key={JSON.stringify(q.data)} data={q.data} />
}
