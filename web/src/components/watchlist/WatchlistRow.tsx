import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AnimateIcon } from '@animate-ui/react/icons'
import { LoaderCircleIcon } from '@/components/animate-ui/icons/loader-circle'
import { RefreshCwIcon } from '@/components/animate-ui/icons/refresh-cw'
import { Trash2Icon } from '@/components/animate-ui/icons/trash-2'
import { useState } from 'react'
import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { TableCell, TableRow } from '@/components/ui/table'
import { formatVnDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { CollectLevel } from '@/api/jobs'
import { ApiError } from '@/api/client'
import { checkNow, levels, removeWatchItem, updateWatchItem, type WatchItem } from '@/api/watchlist'

function checkResultText(n: number) {
  if (n === 0) return 'No new videos'
  return n === 1 ? '1 new video' : `${n} new videos`
}

// Một dòng của bảng watchlist. Mỗi dòng có mutation riêng để Check now của kênh này không chặn kênh khác.
export default function WatchlistRow({ item }: { item: WatchItem }) {
  const queryClient = useQueryClient()
  const [confirming, setConfirming] = useState(false)
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['watchlist'] })

  const update = useMutation({
    mutationFn: (patch: Partial<Pick<WatchItem, 'enabled' | 'level'>>) => updateWatchItem(item.id, patch),
    onSuccess: refresh,
  })
  const check = useMutation({ mutationFn: () => checkNow(item.id), onSuccess: refresh })
  const remove = useMutation({
    mutationFn: () => removeWatchItem(item.id),
    onSuccess: () => {
      setConfirming(false)
      refresh()
    },
  })

  return (
    <TableRow className="align-top">
      <TableCell className={cn('font-medium', !item.enabled && 'text-muted-foreground')}>
        {item.title}
        {!item.initialized && (
          <span className="mt-1 flex items-center gap-1 text-xs font-normal text-muted-foreground">
            <LoaderCircleIcon className="size-3" animate />
            Setting up…
          </span>
        )}
        {item.last_error && (
          <p className="mt-1 max-w-64 text-xs font-normal [overflow-wrap:anywhere] text-destructive">{item.last_error}</p>
        )}
      </TableCell>
      <TableCell className="text-muted-foreground">{item.handle || '—'}</TableCell>
      <TableCell>
        <Switch
          aria-label={`Watch ${item.title}`}
          checked={item.enabled}
          disabled={update.isPending}
          onCheckedChange={(enabled) => update.mutate({ enabled })}
        />
      </TableCell>
      <TableCell>
        <Select value={item.level} onValueChange={(v) => update.mutate({ level: v as CollectLevel })}>
          <SelectTrigger size="sm" className="w-28" aria-label={`Collect level for ${item.title}`}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {levels.map((l) => (
              <SelectItem key={l} value={l}>
                {l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell className="text-xs">{item.last_checked_at ? formatVnDateTime(item.last_checked_at) : 'Never'}</TableCell>
      <TableCell className="max-w-64">
        {item.latest_video ? (
          <>
            <Link
              to={`/videos/${item.latest_video.id}`}
              className="block truncate hover:underline"
              title={item.latest_video.title}
            >
              {item.latest_video.title}
            </Link>
            {item.latest_video.published_at && (
              <span className="text-xs text-muted-foreground">{formatVnDateTime(item.latest_video.published_at)}</span>
            )}
          </>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </TableCell>
      <TableCell className="text-right">{item.collected_count}</TableCell>
      <TableCell>
        <div className="flex items-center justify-end gap-1">
          <span className="text-xs text-muted-foreground" aria-live="polite">
            {check.isPending && 'Checking…'}
            {check.isSuccess && checkResultText(check.data.new_videos.length)}
            {check.isError && (
              <span className="text-destructive">
                {check.error instanceof ApiError && check.error.status === 502 ? check.error.message : 'Check failed'}
              </span>
            )}
          </span>
          <span title={item.enabled ? undefined : 'Enable the channel to check it'}>
            <AnimateIcon animateOnHover asChild>
              <Button variant="outline" size="sm" disabled={check.isPending || !item.enabled} onClick={() => check.mutate()}>
                {check.isPending ? <LoaderCircleIcon animate /> : <RefreshCwIcon />}
                Check now
              </Button>
            </AnimateIcon>
          </span>
          <AnimateIcon animateOnHover asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={`Remove ${item.title}`}
              onClick={() => setConfirming(true)}
            >
              <Trash2Icon />
            </Button>
          </AnimateIcon>
        </div>
      </TableCell>

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove {item.title}?</DialogTitle>
            <DialogDescription>
              The channel will no longer be checked for new videos. Videos and captures already collected are
              kept.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button variant="destructive" disabled={remove.isPending} onClick={() => remove.mutate()}>
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </TableRow>
  )
}
