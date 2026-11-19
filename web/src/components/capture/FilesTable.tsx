import { useMutation } from '@tanstack/react-query'
import { Check, Copy, Download } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatVnDateTime } from '@/lib/format'
import { captureFileUrl, type CaptureDetail, type VerifyFile, verifyCapture } from '@/api/videos'
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

export default function FilesTable({ videoId, captureId, capture }: { videoId: string; captureId: string; capture: CaptureDetail }) {
  const verify = useMutation({
    mutationFn: () => verifyCapture(videoId, captureId),
  })
  const sizes = new Map(capture.files.map((f) => [f.path, f.bytes]))

  // Danh sách hiển thị: theo manifest; sau khi verify thì theo kết quả (có thêm file `unexpected`).
  const result = verify.data
  const rows: VerifyFile[] =
    result?.files ??
    capture.files.map((f) => ({ path: f.path, status: 'OK', expected_sha256: f.sha256, actual_sha256: f.sha256 }))
  const counts = { OK: 0, FAIL: 0, missing: 0, unexpected: 0 }
  for (const f of result?.files ?? []) counts[f.status]++
  const allOk = result && counts.FAIL + counts.missing + counts.unexpected === 0

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Files ({capture.files.length})</CardTitle>
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
            <span className="text-muted-foreground">Checked {formatVnDateTime(result.checked_at)}</span>
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
              const sha256 = f.expected_sha256 ?? f.actual_sha256 ?? ''
              const bytes = sizes.get(f.path)
              return (
                <TableRow key={f.path}>
                  <TableCell>
                    <code className="break-all">{f.path}</code>
                  </TableCell>
                  <TableCell className="text-right">{bytes === undefined ? '—' : formatBytes(bytes)}</TableCell>
                  <TableCell>
                    {sha256 && <CopyHash sha256={sha256} />}
                    {f.status === 'FAIL' && f.actual_sha256 && (
                      <div className="px-2 font-mono text-xs text-destructive" title={f.actual_sha256}>
                        actual {shortHash(f.actual_sha256)}
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
                      <Button asChild variant="ghost" size="icon-sm">
                        <a
                          href={captureFileUrl(videoId, captureId, f.path)}
                          download={f.path.split('/').pop()}
                          aria-label={`Download ${f.path}`}
                        >
                          <Download />
                        </a>
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
