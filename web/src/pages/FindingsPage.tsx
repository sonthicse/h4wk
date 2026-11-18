import { useParams } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { findings, type Severity } from '@/mocks/data'

const severityVariant: Record<Severity, 'destructive' | 'default' | 'secondary'> = {
  high: 'destructive',
  medium: 'default',
  low: 'secondary',
}

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

export default function FindingsPage() {
  const { caseId } = useParams()
  const rows = findings.filter((f) => f.caseId === caseId)

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Findings</h1>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Video</TableHead>
            <TableHead>Time</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Quote</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Severity</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((f) => (
            <TableRow key={f.id}>
              <TableCell className="max-w-48 truncate">{f.videoTitle}</TableCell>
              <TableCell className="font-mono">
                {f.sourceKind === 'comment' ? '—' : `${formatTime(f.start)}–${formatTime(f.end)}`}
              </TableCell>
              <TableCell>{f.sourceKind}</TableCell>
              <TableCell className="max-w-96 truncate">{f.quote}</TableCell>
              <TableCell>{f.category}</TableCell>
              <TableCell>
                <Badge variant={severityVariant[f.severity]}>{f.severity}</Badge>
              </TableCell>
              <TableCell>
                <Badge variant="outline">{f.status}</Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
