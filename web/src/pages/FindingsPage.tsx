import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { findings, type Finding, type ReviewStatus, type Severity } from '@/mocks/data'

const severityVariant: Record<Severity, 'destructive' | 'default' | 'secondary'> = {
  high: 'destructive',
  medium: 'default',
  low: 'secondary',
}

const statusVariant: Record<ReviewStatus, 'outline' | 'default' | 'secondary' | 'destructive'> = {
  pending: 'outline',
  confirmed: 'default',
  rejected: 'secondary',
  needs_info: 'outline',
}

const severityRank: Record<Severity, number> = { high: 0, medium: 1, low: 2 }

// Các nguồn có mốc thời gian trong video; nguồn còn lại (tiêu đề, mô tả, thumbnail, comment) thì không.
const timedSources = new Set(['speech', 'ocr', 'visual'])

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

function timeRange(f: Finding) {
  return timedSources.has(f.sourceKind) ? `${formatTime(f.start)}–${formatTime(f.end)}` : '—'
}

function videoLink(f: Finding) {
  return `/cases/${f.caseId}/videos/${f.videoId}?finding=${f.id}`
}

type Filters = { q: string; severity: string; category: string; source: string; status: string }
const emptyFilters: Filters = { q: '', severity: 'all', category: 'all', source: 'all', status: 'all' }

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

function FindingSheet({ finding, onClose }: { finding: Finding | null; onClose: () => void }) {
  return (
    <Sheet open={finding !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-[28rem] sm:max-w-md">
        {finding && (
          <>
            <SheetHeader>
              <SheetTitle>{finding.videoTitle}</SheetTitle>
              <SheetDescription>
                {finding.channel} · {finding.sourceKind} · {timeRange(finding)}
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
                <Badge variant={statusVariant[finding.status]}>{finding.status}</Badge>
              </div>
              <Detail label="Entity">{finding.entity}</Detail>
              <Detail label="Reason">{finding.reason}</Detail>
              <Detail label="Triggers">
                <ul className="space-y-1">
                  {finding.triggers.map((t) => (
                    <li key={t.via} className="font-mono text-xs">
                      {t.via} · score {t.score.toFixed(2)}
                    </li>
                  ))}
                </ul>
              </Detail>
              <Detail label="Analyzer">
                {finding.analyzer}
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
  const { caseId } = useParams()
  const [filters, setFilters] = useState<Filters>(emptyFilters)
  const [selected, setSelected] = useState<Finding | null>(null)

  const caseFindings = findings.filter((f) => f.caseId === caseId)
  const q = filters.q.trim().toLowerCase()
  const rows = caseFindings
    .filter((f) => filters.severity === 'all' || f.severity === filters.severity)
    .filter((f) => filters.category === 'all' || f.category === filters.category)
    .filter((f) => filters.source === 'all' || f.sourceKind === filters.source)
    .filter((f) => filters.status === 'all' || f.status === filters.status)
    .filter((f) => !q || `${f.quote} ${f.videoTitle} ${f.entity}`.toLowerCase().includes(q))
    .sort((a, b) => severityRank[a.severity] - severityRank[b.severity] || a.videoTitle.localeCompare(b.videoTitle) || a.start - b.start)

  const set = (key: keyof Filters) => (value: string) => setFilters((f) => ({ ...f, [key]: value }))
  const count = (s: Severity) => caseFindings.filter((f) => f.severity === s).length
  const pending = caseFindings.filter((f) => f.status === 'pending').length
  const isFiltered = JSON.stringify(filters) !== JSON.stringify(emptyFilters)

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Findings</h1>
        <div className="flex gap-2 text-sm">
          <Badge variant="destructive">{count('high')} high</Badge>
          <Badge variant="default">{count('medium')} medium</Badge>
          <Badge variant="secondary">{count('low')} low</Badge>
          <Badge variant="outline">{pending} pending review</Badge>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="w-64"
          placeholder="Search quote, video or entity…"
          value={filters.q}
          onChange={(e) => set('q')(e.target.value)}
        />
        <FilterSelect label="Severities" value={filters.severity} options={['high', 'medium', 'low']} onChange={set('severity')} />
        <FilterSelect
          label="Categories"
          value={filters.category}
          options={['insult', 'unsupported_accusation', 'fabrication', 'legitimate_criticism', 'neutral']}
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
          options={['pending', 'confirmed', 'rejected', 'needs_info']}
          onChange={set('status')}
        />
        {isFiltered && (
          <Button variant="ghost" onClick={() => setFilters(emptyFilters)}>
            Clear
          </Button>
        )}
        <span className="ml-auto text-sm text-muted-foreground">
          {rows.length} of {caseFindings.length}
        </span>
      </div>

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
            <TableRow key={f.id} className="cursor-pointer" onClick={() => setSelected(f)}>
              <TableCell className="max-w-48 truncate">{f.videoTitle}</TableCell>
              <TableCell className="font-mono">
                {timedSources.has(f.sourceKind) ? (
                  <Link to={videoLink(f)} className="hover:underline" onClick={(e) => e.stopPropagation()}>
                    {timeRange(f)}
                  </Link>
                ) : (
                  '—'
                )}
              </TableCell>
              <TableCell>{f.sourceKind}</TableCell>
              <TableCell className="whitespace-nowrap">{f.entity}</TableCell>
              <TableCell className="max-w-80 truncate">{f.quote}</TableCell>
              <TableCell>{f.category}</TableCell>
              <TableCell>
                <Badge variant={severityVariant[f.severity]}>{f.severity}</Badge>
              </TableCell>
              <TableCell>{f.confidence}</TableCell>
              <TableCell>
                <Badge variant={statusVariant[f.status]}>{f.status}</Badge>
              </TableCell>
            </TableRow>
          ))}
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={9} className="text-center text-muted-foreground">
                No findings match these filters.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <FindingSheet finding={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
