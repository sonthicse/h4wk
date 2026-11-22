import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { listEntities } from '@/api/entities'
import type { Finding } from '@/api/findings'
import { listQueue, type ReviewStatus } from '@/api/review'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatTime, severityRank, severityVariant, showReason } from '@/lib/findings'

type Severity = Finding['severity']
type Filters = { q: string; severity: string; category: string; source: string; status: string }
const emptyFilters: Filters = { q: '', severity: 'all', category: 'all', source: 'all', status: 'all' }

const statusVariant: Record<ReviewStatus, 'outline' | 'default' | 'secondary'> = {
  unreviewed: 'outline',
  confirmed: 'default',
  rejected: 'secondary',
  needs_info: 'outline',
}

function timeRange(f: Finding) {
  return f.start == null ? '—' : `${formatTime(f.start)}–${formatTime(f.end ?? f.start)}`
}

// Mở trang Video detail tại đúng nghi vấn (trang tự nhảy tới start − 2s).
function videoLink(f: Finding) {
  return `/videos/${encodeURIComponent(f.video_id)}?finding=${encodeURIComponent(f.id)}`
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  onChange: (v: string) => void
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-44" aria-label={label}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All {label.toLowerCase()}</SelectItem>
        {options.map((o) => (
          <SelectItem key={o} value={o}>{o}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}

function FindingSheet({
  finding,
  entityName,
  onClose,
}: {
  finding: Finding | null
  entityName: (id: string | null | undefined) => string
  onClose: () => void
}) {
  return (
    <Sheet open={finding !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent>
        {finding && (
          <>
            <SheetHeader>
              <SheetTitle className="font-mono">{finding.video_id}</SheetTitle>
              <SheetDescription>
                {finding.source_kind} · {timeRange(finding)} · capture {finding.capture}
              </SheetDescription>
            </SheetHeader>
            <dl className="space-y-4 overflow-y-auto px-4">
              <Detail label="Quote">
                <blockquote className="border-l-2 pl-3 italic">{finding.quote}</blockquote>
              </Detail>
              <div className="flex flex-wrap gap-2">
                <Badge variant={severityVariant[finding.severity]}>{finding.severity}</Badge>
                <Badge variant="outline">{finding.category}</Badge>
                <Badge variant="outline">{finding.confidence}</Badge>
              </div>
              <Detail label="Entity">{entityName(finding.entity)}</Detail>
              {showReason(finding) && <Detail label="Reason">{finding.reason}</Detail>}
              <Detail label="Triggers">
                <ul className="space-y-1">
                  {(finding.triggers ?? []).map((t, i) => (
                    <li key={i} className="font-mono text-xs">
                      {t.via}
                      {t.score != null && ` · score ${t.score.toFixed(2)}`}
                    </li>
                  ))}
                </ul>
              </Detail>
              <Detail label="Analyzer">
                {finding.analyzer} {finding.analyzer_version}
                {finding.model && (
                  <span className="text-muted-foreground"> · {finding.model.provider}/{finding.model.model}</span>
                )}
              </Detail>
              <Button asChild className="w-full">
                <Link to={videoLink(finding)}>Open in video</Link>
              </Button>
            </dl>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}

export default function FindingsPage() {
  const [filters, setFilters] = useState<Filters>(emptyFilters)
  const [selected, setSelected] = useState<Finding | null>(null)

  // Dùng hàng đợi rà soát để có trạng thái của từng nghi vấn (chỉ lần phân tích mới nhất mỗi bản thu).
  const findings = useQuery({ queryKey: ['review-queue'], queryFn: () => listQueue() })
  const statusOf = (f: Finding): ReviewStatus => findings.data?.find((it) => it.finding.id === f.id)?.status ?? 'unreviewed'
  const entities = useQuery({ queryKey: ['entities'], queryFn: listEntities })
  // Nghi vấn chỉ ghi id đối tượng (e_01); tên lấy từ danh sách đối tượng.
  // Vi phạm xét theo nội dung (violence, hate, forgery, state_secret) có thể không có đối tượng.
  const entityName = (id: string | null | undefined) => (id ? (entities.data?.find((e) => e.id === id)?.name ?? id) : '—')

  const allFindings = (findings.data ?? []).map((it) => it.finding)
  const q = filters.q.trim().toLowerCase()
  const rows = allFindings
    .filter((f) => filters.severity === 'all' || f.severity === filters.severity)
    .filter((f) => filters.category === 'all' || f.category === filters.category)
    .filter((f) => filters.source === 'all' || f.source_kind === filters.source)
    .filter((f) => filters.status === 'all' || statusOf(f) === filters.status)
    .filter((f) => !q || `${f.quote} ${f.video_id} ${entityName(f.entity)}`.toLowerCase().includes(q))
    .sort(
      (a, b) =>
        severityRank[a.severity] - severityRank[b.severity] ||
        a.video_id.localeCompare(b.video_id) ||
        (a.start ?? 0) - (b.start ?? 0),
    )

  const set = (key: keyof Filters) => (value: string) => setFilters((f) => ({ ...f, [key]: value }))
  const count = (s: Severity) => allFindings.filter((f) => f.severity === s).length
  const isFiltered = JSON.stringify(filters) !== JSON.stringify(emptyFilters)

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Findings</h1>
        <div className="flex gap-2 text-sm">
          <Badge variant="destructive">{count('high')} high</Badge>
          <Badge variant="default">{count('medium')} medium</Badge>
          <Badge variant="secondary">{count('low')} low</Badge>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="w-64"
          aria-label="Search findings"
          placeholder="Search quote, video or entity…"
          value={filters.q}
          onChange={(e) => set('q')(e.target.value)}
        />
        <FilterSelect label="Severities" value={filters.severity} options={['high', 'medium', 'low']} onChange={set('severity')} />
        <FilterSelect
          label="Categories"
          value={filters.category}
          options={['insult', 'unsupported_accusation', 'fabrication', 'incitement', 'violence', 'hate', 'forgery', 'state_secret', 'legitimate_criticism', 'neutral']}
          onChange={set('category')}
        />
        <FilterSelect
          label="Sources"
          value={filters.source}
          options={['speech', 'ocr', 'visual', 'title', 'description', 'thumbnail', 'comment']}
          onChange={set('source')}
        />
        <FilterSelect
          label="Statuses"
          value={filters.status}
          options={['unreviewed', 'confirmed', 'rejected', 'needs_info']}
          onChange={set('status')}
        />
        {isFiltered && (
          <Button variant="ghost" onClick={() => setFilters(emptyFilters)}>
            Clear
          </Button>
        )}
        <span className="ml-auto text-sm text-muted-foreground">
          {rows.length} of {allFindings.length}
        </span>
      </div>

      {findings.error && <p className="text-sm text-destructive">Could not load findings: {findings.error.message}</p>}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Video</TableHead>
            <TableHead>Time</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Entity</TableHead>
            <TableHead>Quote</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Severity</TableHead>
            <TableHead>Confidence</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((f) => (
            <TableRow
              key={f.id}
              tabIndex={0}
              className="cursor-pointer focus-visible:bg-muted focus-visible:outline-none"
              onClick={() => setSelected(f)}
              onKeyDown={(e) => {
                if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
                  e.preventDefault()
                  setSelected(f)
                }
              }}
            >
              <TableCell className="font-mono text-xs">{f.video_id}</TableCell>
              <TableCell className="font-mono">
                {f.start == null ? (
                  '—'
                ) : (
                  <Link to={videoLink(f)} className="hover:underline" onClick={(e) => e.stopPropagation()}>
                    {timeRange(f)}
                  </Link>
                )}
              </TableCell>
              <TableCell>{f.source_kind}</TableCell>
              <TableCell className="whitespace-nowrap">{entityName(f.entity)}</TableCell>
              {/* Cột Quote lấy phần rộng còn lại và cắt chữ, để bảng vừa khung không cuộn ngang. */}
              <TableCell className="w-full max-w-0 truncate" title={f.quote}>
                {f.quote}
              </TableCell>
              <TableCell>{f.category}</TableCell>
              <TableCell>
                <Badge variant={severityVariant[f.severity]}>{f.severity}</Badge>
              </TableCell>
              <TableCell>{f.confidence}</TableCell>
              <TableCell>
                <Badge variant={statusVariant[statusOf(f)]}>{statusOf(f)}</Badge>
              </TableCell>
            </TableRow>
          ))}
          {findings.isPending && (
            <TableRow highlight={false}>
              <TableCell colSpan={9} className="text-center text-muted-foreground">
                Loading…
              </TableCell>
            </TableRow>
          )}
          {findings.data && rows.length === 0 && (
            <TableRow highlight={false}>
              <TableCell colSpan={9} className="text-center text-muted-foreground">
                {allFindings.length === 0 ? 'No findings yet. Collect a video to analyze it.' : 'No findings match these filters.'}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <FindingSheet finding={selected} entityName={entityName} onClose={() => setSelected(null)} />
    </div>
  )
}
