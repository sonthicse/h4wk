import { useMutation } from '@tanstack/react-query'
import { Check, Copy, Download } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatVnDateTime } from '@/lib/format'
import { type Capture, type VerifyFile, verifyCapture } from '@/mocks/captures'
import { formatBytes, shortHash, verifyStatusVariant } from './helpers'

function CopyHash({ sha256 }: { sha256: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <Button
      variant="ghost"
      size="sm"
      className="font-mono text-xs"
      title={sha256}
      aria-label={`Copy SHA-256 ${sha256}`}
      onClick={() => {
        navigator.clipboard?.writeText(sha256)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      }}
    >
      {shortHash(sha256)}
      {copied ? <Check /> : <Copy />}
    </Button>
  )
}

// Bản demo: tải một blob nhỏ thay cho file thật trên đĩa.
function downloadDemo(path: string, sha256: string) {
  const blob = new Blob([`Demo content for ${path}\nsha256: ${sha256}\n`], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = path.split('/').pop() ?? 'file'
  a.click()
  URL.revokeObjectURL(url)
}

export default function FilesTable({ capture }: { capture: Capture }) {
  const verify = useMutation({
    mutationFn: () => verifyCapture(capture.caseId, capture.videoId, capture.id),
  })

  // Danh sách hiển thị: theo manifest; sau khi verify thì theo kết quả (có thêm file `unexpected`).
  const result = verify.data
  const rows: VerifyFile[] =
    result?.files ??
    Object.entries(capture.manifest.files).map(([path, expected]) => ({ path, status: 'OK', expected }))
  const counts = { OK: 0, FAIL: 0, missing: 0, unexpected: 0 }
  for (const f of result?.files ?? []) counts[f.status]++
  const allOk = result && counts.FAIL + counts.missing + counts.unexpected === 0

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Files ({Object.keys(capture.manifest.files).length})</CardTitle>
        <Button onClick={() => verify.mutate()} disabled={verify.isPending}>
          {verify.isPending ? 'Verifying…' : 'Verify integrity'}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {verify.error && <p className="text-sm text-destructive">Verification failed to run.</p>}
        {result && (
          <p role="status" className={`text-sm ${allOk ? '' : 'text-destructive'}`}>
            {allOk
              ? `All ${counts.OK} files match the manifest.`
              : `${counts.OK} OK, ${counts.FAIL} FAIL, ${counts.missing} missing, ${counts.unexpected} unexpected.`}{' '}
            <span className="text-muted-foreground">Checked {formatVnDateTime(result.checkedAt)}</span>
          </p>
        )}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Path</TableHead>
              <TableHead className="text-right">Size</TableHead>
              <TableHead>SHA-256</TableHead>
              {result && <TableHead>Integrity</TableHead>}
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((f) => {
              const entry = f.expected ?? f.actual!
              return (
                <TableRow key={f.path}>
                  <TableCell>
                    <code className="break-all">{f.path}</code>
                  </TableCell>
                  <TableCell className="text-right">{formatBytes(entry.bytes)}</TableCell>
                  <TableCell>
                    <CopyHash sha256={entry.sha256} />
                    {f.status === 'FAIL' && f.actual && (
                      <div className="px-2 font-mono text-xs text-destructive" title={f.actual.sha256}>
                        actual {shortHash(f.actual.sha256)}
                      </div>
                    )}
                  </TableCell>
                  {result && (
                    <TableCell>
                      <Badge variant={verifyStatusVariant(f.status)}>{f.status}</Badge>
                    </TableCell>
                  )}
                  <TableCell>
                    {f.status !== 'unexpected' && f.status !== 'missing' && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Download ${f.path}`}
                        onClick={() => downloadDemo(f.path, entry.sha256)}
                      >
                        <Download />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
