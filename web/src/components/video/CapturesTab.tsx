import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatVnDateTime } from '@/lib/format'
import type { CaptureSummary } from '@/api/videos'

export default function CapturesTab({ captures, videoId }: { captures: CaptureSummary[]; videoId: string }) {
  if (captures.length === 0) return <p className="py-4 text-sm text-muted-foreground">No captures yet.</p>

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Capture</TableHead>
          <TableHead>Level</TableHead>
          <TableHead>Captured at (VN)</TableHead>
          <TableHead>Transcripts</TableHead>
          <TableHead className="text-right">Comments</TableHead>
          <TableHead className="text-right">Keyframes</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {captures.map((c, i) => (
          <TableRow key={c.id}>
            <TableCell className="font-mono">
              <Link to={`/videos/${videoId}/captures/${c.id}`} className="hover:underline">
                {c.id}
              </Link>
              {i === 0 && <Badge variant="secondary" className="ml-2">latest</Badge>}
            </TableCell>
            <TableCell><Badge variant="outline">{c.level}</Badge></TableCell>
            <TableCell>{formatVnDateTime(c.collected_at)}</TableCell>
            <TableCell className="space-x-1">
              {c.transcript_kinds.length === 0 ? '—' : c.transcript_kinds.map((k) => <Badge key={k} variant="outline">{k}</Badge>)}
            </TableCell>
            <TableCell className="text-right">{c.comment_count}</TableCell>
            <TableCell className="text-right">{c.keyframe_count}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
