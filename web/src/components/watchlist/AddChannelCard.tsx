import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { CollectLevel } from '@/api/jobs'
import { addWatchItem, levels } from '@/api/watchlist'
import { useWatchlistSettings } from '@/hooks/use-watchlist-settings'

// Form thêm kênh vào watchlist (SPEC 10.9). Mức thu mặc định là `full` (SPEC 10.7).
export default function AddChannelCard() {
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const [level, setLevel] = useState<CollectLevel>('full')
  const [added, setAdded] = useState<string | null>(null)
  const { initial_videos, check_interval_min } = useWatchlistSettings()

  const add = useMutation({
    mutationFn: () => addWatchItem(input, level),
    onSuccess: (item) => {
      setAdded(`${item.title} added. Its ${initial_videos} latest videos are being collected at ${item.level} level.`)
      setInput('')
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add channel</CardTitle>
        <CardDescription>
          When a channel is added, its {initial_videos} latest videos are collected and processed right away. After
          that, enabled channels are checked by RSS every {check_interval_min} minutes and each new video is collected
          automatically.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault()
            setAdded(null)
            if (input.trim()) add.mutate()
          }}
        >
          <div className="flex-1 space-y-2">
            <Label htmlFor="watch-input">Channel link or @handle</Label>
            <Input
              id="watch-input"
              placeholder="https://www.youtube.com/@handle or @handle"
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                add.reset()
              }}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="watch-level">Level</Label>
            <Select value={level} onValueChange={(v) => setLevel(v as CollectLevel)}>
              <SelectTrigger id="watch-level" className="w-36">
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
          </div>
          <Button type="submit" disabled={!input.trim() || add.isPending}>
            {add.isPending ? 'Adding…' : 'Add to watchlist'}
          </Button>
        </form>
        {add.error && <p className="text-sm text-destructive">{add.error.message}</p>}
        {added && <p className="text-sm text-muted-foreground">{added}</p>}
      </CardContent>
    </Card>
  )
}
