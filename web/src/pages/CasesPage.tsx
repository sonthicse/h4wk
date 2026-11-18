import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { cases } from '@/mocks/data'

export default function CasesPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Cases</h1>
        <Button>New case</Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Entities</TableHead>
            <TableHead className="text-right">Videos</TableHead>
            <TableHead className="text-right">Open findings</TableHead>
            <TableHead>Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {cases.map((c) => (
            <TableRow key={c.id}>
              <TableCell>
                <Link to={`/cases/${c.id}/dashboard`} className="font-medium hover:underline">
                  {c.name}
                </Link>
              </TableCell>
              <TableCell className="space-x-1">
                {c.entities.map((e) => (
                  <Badge key={e} variant="secondary">{e}</Badge>
                ))}
              </TableCell>
              <TableCell className="text-right">{c.videoCount}</TableCell>
              <TableCell className="text-right">{c.openFindings}</TableCell>
              <TableCell>{new Date(c.updatedAt).toLocaleString('en-GB')}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
