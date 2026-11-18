import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatVnTime } from '@/lib/format'
import type { SourceCall } from '@/mocks/captures'
import { sourceStatusVariant } from './helpers'

function formatCost(cost: SourceCall['cost']) {
  const parts = []
  if (cost?.quotaUnits) parts.push(`${cost.quotaUnits} quota ${cost.quotaUnits === 1 ? 'unit' : 'units'}`)
  if (cost?.credits) parts.push(`${cost.credits} ${cost.credits === 1 ? 'credit' : 'credits'}`)
  if (parts.length) return parts.join(', ')
  return cost ? 'free' : '—' // có ghi chi phí nhưng bằng 0: miễn phí
}

export default function SourcesTable({ sources }: { sources: SourceCall[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Sources called</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Provider</TableHead>
              <TableHead>What</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Started</TableHead>
              <TableHead className="text-right">Duration</TableHead>
              <TableHead>Cost</TableHead>
              <TableHead>Error</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sources.map((s, i) => (
              <TableRow key={i}>
                <TableCell>
                  {s.provider ?? <span className="text-muted-foreground">—</span>}
                  {s.version && <span className="ml-1 text-xs text-muted-foreground">{s.version}</span>}
                </TableCell>
                <TableCell>
                  <code>{s.what}</code>
                </TableCell>
                <TableCell>
                  <Badge variant={sourceStatusVariant(s.status)}>{s.status}</Badge>
                </TableCell>
                <TableCell>{s.startedAt ? formatVnTime(s.startedAt) : '—'}</TableCell>
                <TableCell className="text-right">{s.durationMs !== undefined ? `${s.durationMs} ms` : '—'}</TableCell>
                <TableCell>{formatCost(s.cost)}</TableCell>
                <TableCell className="max-w-xs whitespace-normal break-words text-xs text-destructive">{s.error}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
