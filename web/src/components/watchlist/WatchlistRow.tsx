import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2Icon, RefreshCwIcon, Trash2Icon } from 'lucide-react'
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
import type { CollectLevel } from '@/mocks/jobs'
import { checkNow, levels, removeWatchItem, updateWatchItem, type WatchItem } from '@/mocks/watchlist'

function checkResultText(n: number) {
  if (n === 0) return 'No new videos'
  return n === 1 ? '1 new video' : `${n} new videos`
}

// Một dòng của bảng watchlist. Mỗi dòng có mutation riêng để Check now của kênh này không chặn kênh khác.
export default function WatchlistRow({ item }: { item: WatchItem }) {
  const queryClient = useQueryClient()
  const [confirming, setConfirming] = useState(false)
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['watchlist', item.caseId] })

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
      <TableCell className={cn('font-medium', !item.enabled && 'text-muted-foreground')}>{item.channelTitle}</TableCell>
      <TableCell className="text-muted-foreground">{item.handle || '—'}</TableCell>
      <TableCell>
        <Switch
          aria-label={`Watch ${item.channelTitle}`}
          checked={item.enabled}
          disabled={update.isPending}
          onCheckedChange={(enabled) => update.mutate({ enabled })}
        />
      </TableCell>
      <TableCell>
        <Select value={item.level} onValueChange={(v) => update.mutate({ level: v as CollectLevel })}>
          <SelectTrigger size="sm" className="w-28" aria-label={`Collect level for ${item.channelTitle}`}>
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
      <TableCell className="text-xs">{item.lastCheckedAt ? formatVnDateTime(item.lastCheckedAt) : 'Never'}</TableCell>
      <TableCell className="max-w-64">
        {item.latestVideo ? (
          <>
            <Link
              to={`/cases/${item.caseId}/videos/${item.latestVideo.videoId}`}
              className="block truncate hover:underline"
              title={item.latestVideo.title}
            >
              {item.latestVideo.title}
            </Link>
            <span className="text-xs text-muted-foreground">{formatVnDateTime(item.latestVideo.publishedAt)}</span>
          </>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </TableCell>
      <TableCell className="text-right">{item.collectedCount}</TableCell>
      <TableCell>
        <div className="flex items-center justify-end gap-1">
          <span className="text-xs text-muted-foreground" aria-live="polite">
            {check.isPending && 'Checking…'}
            {check.isSuccess && checkResultText(check.data.newVideos)}
            {check.isError && <span className="text-destructive">Check failed</span>}
          </span>
          <Button variant="outline" size="sm" disabled={check.isPending} onClick={() => check.mutate()}>
            {check.isPending ? <Loader2Icon className="animate-spin" /> : <RefreshCwIcon />}
            Check now
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Remove ${item.channelTitle}`}
            onClick={() => setConfirming(true)}
          >
            <Trash2Icon />
          </Button>
        </div>
      </TableCell>

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove {item.channelTitle}?</DialogTitle>
            <DialogDescription>
              The channel will no longer be checked for new videos. Videos and captures already collected stay in the
              case.
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
