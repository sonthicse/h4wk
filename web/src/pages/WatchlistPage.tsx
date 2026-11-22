import { useQuery } from '@tanstack/react-query'
import { InfoIcon } from 'lucide-react'
import AddChannelCard from '@/components/watchlist/AddChannelCard'
import WatchlistRow from '@/components/watchlist/WatchlistRow'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { listWatchItems } from '@/api/watchlist'
import { useWatchlistSettings } from '@/hooks/use-watchlist-settings'

export default function WatchlistPage() {
  const { check_interval_min } = useWatchlistSettings()
  const items = useQuery({ queryKey: ['watchlist'], queryFn: listWatchItems,

    refetchInterval: (q) => (q.state.data?.some((w) => !w.initialized) ? 5000 : false),
  })

  const all = items.data ?? []
  const enabled = all.filter((w) => w.enabled).length

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Watchlist</h1>
        <div className="flex gap-2 text-sm">
          <Badge variant="outline">{all.length} {all.length === 1 ? 'channel' : 'channels'}</Badge>
          <Badge variant="outline">{enabled} enabled</Badge>
        </div>
      </div>

      <AddChannelCard />

      <div className="space-y-2">
        <h2 className="text-lg font-semibold">Channels</h2>
        <Alert>
          <InfoIcon />
          <AlertDescription>
            Enabled channels are checked by RSS every {check_interval_min} minutes. YouTube caches RSS feeds for up to
            15 minutes, so a new video can appear late. Check now checks a channel immediately using RSS and the
            channel's uploads playlist from the YouTube API.
          </AlertDescription>
        </Alert>
        {items.error && <p className="text-sm text-destructive">Could not load the watchlist: {items.error.message}</p>}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Channel</TableHead>
              <TableHead>Handle</TableHead>
              <TableHead>Watch</TableHead>
              <TableHead>Level</TableHead>
              <TableHead>Last checked</TableHead>
              <TableHead>Latest video</TableHead>
              <TableHead className="text-right">Collected</TableHead>
              <TableHead>
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {all.map((item) => (
              <WatchlistRow key={item.id} item={item} />
            ))}
            {items.data?.length === 0 && (
              <TableRow highlight={false}>
                <TableCell colSpan={8} className="text-center text-muted-foreground">
                  No channels in this watchlist yet. Add a channel link or @handle above.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
