import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { listVideos } from '@/api/videos'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatVnDateTime } from '@/lib/format'

// Danh sách video đã thu (GET /api/videos), mới thu trước.
// Mã bản thu YYYYMMDDTHHMMSS đã là giờ Việt Nam: đổi sang HH:MM dd/mm/yyyy.
const captureLabel = (id: string) => {
  const m = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})\d{2}$/.exec(id)
  return m ? `${m[4]}:${m[5]} ${m[3]}/${m[2]}/${m[1]}` : id
}

export default function VideosPage() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const videos = useQuery({ queryKey: ['videos'], queryFn: listVideos })

  const all = videos.data ?? []
  const query = q.trim().toLowerCase()
  const rows = all.filter((v) => !query || `${v.title ?? ''} ${v.channel ?? ''} ${v.id}`.toLowerCase().includes(query))

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Videos</h1>
        <Badge variant="outline">
          {all.length} {all.length === 1 ? 'video' : 'videos'}
        </Badge>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="w-64"
          aria-label="Search videos"
          placeholder="Search title, channel or ID…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {q && (
          <Button variant="ghost" onClick={() => setQ('')}>
            Clear
          </Button>
        )}
        <span className="ml-auto text-sm text-muted-foreground">
          {rows.length} of {all.length}
        </span>
        <Button asChild>
          <Link to="/collect">Collect a video</Link>
        </Button>
      </div>

      {videos.error && <p className="text-sm text-destructive">Could not load videos: {videos.error.message}</p>}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Title</TableHead>
            <TableHead>Channel</TableHead>
            <TableHead>Published</TableHead>
            <TableHead className="text-right">Views</TableHead>
            <TableHead>Findings</TableHead>
            <TableHead>Latest capture</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((v) => {
            const open = () => navigate(`/videos/${v.id}`)
            return (
              <TableRow
                key={v.id}
                tabIndex={0}
                className="cursor-pointer focus-visible:bg-muted focus-visible:outline-none"
                onClick={open}
                onKeyDown={(e) => {
                  if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
                    e.preventDefault()
                    open()
                  }
                }}
              >
                <TableCell className="max-w-96">
                  <p className="truncate font-medium">{v.title ?? v.id}</p>
                  <p className="font-mono text-xs text-muted-foreground">{v.id}</p>
                </TableCell>
                <TableCell>{v.channel ?? '—'}</TableCell>
                <TableCell>{v.published_at ? formatVnDateTime(v.published_at) : '—'}</TableCell>
                <TableCell className="text-right tabular-nums">{v.view_count?.toLocaleString('en-GB') ?? '—'}</TableCell>
                <TableCell className="space-x-1">
                  {v.findings.high > 0 && <Badge variant="destructive">{v.findings.high} high</Badge>}
                  {v.findings.medium > 0 && <Badge variant="default">{v.findings.medium} medium</Badge>}
                  {v.findings.low > 0 && <Badge variant="secondary">{v.findings.low} low</Badge>}
                  {v.findings.high + v.findings.medium + v.findings.low === 0 && (
                    <span className="text-sm text-muted-foreground">None</span>
                  )}
                </TableCell>
                <TableCell>
                  {v.latest_capture ? (
                    <Link
                      to={`/videos/${v.id}/captures/${v.latest_capture}`}
                      className="font-mono text-xs hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {captureLabel(v.latest_capture)}
                    </Link>
                  ) : (
                    '—'
                  )}
                </TableCell>
              </TableRow>
            )
          })}
          {videos.isPending && (
            <TableRow highlight={false}>
              <TableCell colSpan={6} className="text-center text-muted-foreground">
                Loading…
              </TableCell>
            </TableRow>
          )}
          {videos.data && rows.length === 0 && (
            <TableRow highlight={false}>
              <TableCell colSpan={6} className="text-center text-muted-foreground">
                {all.length === 0 ? 'No videos yet. Collect one to start.' : 'No videos match this search.'}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
