import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { severityRank, severityVariant, statusVariant, timeRange, videoLink } from '@/lib/findings'
import { formatVnDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import { findings, type Finding, type ReviewStatus } from '@/mocks/data'

// Quyết định rà soát theo hợp đồng C4 (reviews.jsonl). Ở bản dữ liệu giả, quyết định chỉ nằm trong state của trang.
type Decision = { status: Exclude<ReviewStatus, 'pending'>; by: string; at: string; note: string }
type View = 'pending' | 'needs_info' | 'all'

const CURRENT_USER = 'user:thi'
const views: { id: View; label: string }[] = [
  { id: 'pending', label: 'Pending' },
  { id: 'needs_info', label: 'Needs info' },
  { id: 'all', label: 'All' },
]

function Kbd({ children }: { children: React.ReactNode }) {
  return <kbd className="rounded border bg-muted px-1.5 font-mono text-[10px] text-muted-foreground">{children}</kbd>
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}

export default function ReviewQueuePage() {
  const { caseId } = useParams()
  const [decisions, setDecisions] = useState<Record<string, Decision[]>>({})
  const [view, setView] = useState<View>('pending')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [rejecting, setRejecting] = useState(false)
  const [note, setNote] = useState('')
  const noteRef = useRef<HTMLTextAreaElement>(null)

  const statusOf = (f: Finding): ReviewStatus => decisions[f.id]?.at(-1)?.status ?? f.status
  const caseFindings = findings
    .filter((f) => f.caseId === caseId)
    .sort((a, b) => severityRank[a.severity] - severityRank[b.severity] || a.videoTitle.localeCompare(b.videoTitle) || a.start - b.start)
  const queue = caseFindings.filter((f) => view === 'all' || statusOf(f) === view)
  const selected = queue.find((f) => f.id === selectedId) ?? queue[0] ?? null
  const counts = {
    pending: caseFindings.filter((f) => statusOf(f) === 'pending').length,
    needs_info: caseFindings.filter((f) => statusOf(f) === 'needs_info').length,
    all: caseFindings.length,
  }

  function select(f: Finding | undefined) {
    if (!f) return
    setSelectedId(f.id)
    setRejecting(false)
    setNote('')
  }

  function move(step: number) {
    if (!selected) return
    select(queue[queue.indexOf(selected) + step])
  }

  function decide(status: Decision['status']) {
    if (!selected) return
    if (status === 'rejected' && !note.trim()) {
      setRejecting(true)
      return
    }
    const decision: Decision = { status, by: CURRENT_USER, at: new Date().toISOString(), note: note.trim() }
    setDecisions((d) => ({ ...d, [selected.id]: [...(d[selected.id] ?? []), decision] }))
    // Sang nghi vấn kế tiếp trong hàng đợi để duyệt liên tục không phải rời trang.
    const i = queue.indexOf(selected)
    const next = queue[i + 1] ?? (i > 0 ? queue[i - 1] : undefined)
    setSelectedId(next?.id ?? null)
    setRejecting(false)
    setNote('')
  }

  useEffect(() => {
    if (rejecting) noteRef.current?.focus()
  }, [rejecting])

  // Phím tắt: j/k hoặc ↓/↑ chuyển nghi vấn, c Confirm, r Reject, n Needs info. Bỏ qua khi đang gõ chữ.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement
      if (target.closest('input, textarea, [role="combobox"]') || e.ctrlKey || e.metaKey || e.altKey) return
      const actions: Record<string, () => void> = {
        j: () => move(1),
        ArrowDown: () => move(1),
        k: () => move(-1),
        ArrowUp: () => move(-1),
        c: () => decide('confirmed'),
        n: () => decide('needs_info'),
        r: () => setRejecting(true),
      }
      const action = actions[e.key]
      if (action) {
        e.preventDefault()
        action()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const history = selected ? (decisions[selected.id] ?? []) : []

  return (
    <div className="flex h-[calc(100svh-3rem-3rem)] flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Review queue</h1>
        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          <Kbd>j</Kbd>/<Kbd>k</Kbd> move · <Kbd>c</Kbd> confirm · <Kbd>r</Kbd> reject · <Kbd>n</Kbd> needs info
        </p>
      </div>

      <div className="flex gap-1">
        {views.map((v) => (
          <Button
            key={v.id}
            size="sm"
            variant={view === v.id ? 'default' : 'ghost'}
            aria-pressed={view === v.id}
            onClick={() => {
              setView(v.id)
              setSelectedId(null)
            }}
          >
            {v.label} <span className="ml-1 opacity-70">{counts[v.id]}</span>
          </Button>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-4">
        <ul className="min-h-0 space-y-1 overflow-y-auto pr-1">
          {queue.map((f) => (
            <li key={f.id}>
              <button
                type="button"
                onClick={() => select(f)}
                aria-current={selected?.id === f.id ? 'true' : undefined}
                className={cn(
                  'w-full rounded-md border p-3 text-left transition-colors hover:bg-muted/50',
                  selected?.id === f.id && 'border-primary bg-muted',
                )}
              >
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant={severityVariant[f.severity]}>{f.severity}</Badge>
                  <span>{f.sourceKind}</span>
                  <span className="font-mono">{timeRange(f)}</span>
                  <Badge variant={statusVariant[statusOf(f)]} className="ml-auto">{statusOf(f)}</Badge>
                </div>
                <p className="mt-2 line-clamp-2 text-sm">{f.quote}</p>
                <p className="mt-1 truncate text-xs text-muted-foreground">{f.videoTitle}</p>
              </button>
            </li>
          ))}
          {queue.length === 0 && (
            <li className="p-6 text-center text-sm text-muted-foreground">Nothing left to review here.</li>
          )}
        </ul>

        {/* key theo nghi vấn để panel cuộn lại về đầu mỗi khi chuyển nghi vấn. */}
        <section key={selected?.id} className="min-h-0 overflow-y-auto rounded-md border p-4">
          {selected ? (
            <div className="space-y-4">
              <div>
                <h2 className="font-semibold">{selected.videoTitle}</h2>
                <p className="text-sm text-muted-foreground">
                  {selected.channel} · {selected.sourceKind} · {timeRange(selected)}
                </p>
              </div>

              {['ocr', 'visual', 'thumbnail'].includes(selected.sourceKind) && (
                <div className="flex h-40 items-center justify-center rounded-md bg-muted text-sm text-muted-foreground">
                  Frame preview (T27)
                </div>
              )}

              <dl className="space-y-4">
                <Detail label="Quote">
                  <blockquote className="border-l-2 pl-3 italic">{selected.quote}</blockquote>
                </Detail>
                <div className="flex flex-wrap gap-2">
                  <Badge variant={severityVariant[selected.severity]}>{selected.severity}</Badge>
                  <Badge variant="outline">{selected.category}</Badge>
                  <Badge variant="outline">{selected.confidence}</Badge>
                </div>
                <Detail label="Entity">{selected.entity}</Detail>
                <Detail label="Reason">{selected.reason}</Detail>
                <Detail label="Triggers">
                  <ul className="space-y-1">
                    {selected.triggers.map((t) => (
                      <li key={t.via} className="font-mono text-xs">
                        {t.via} · score {t.score.toFixed(2)}
                      </li>
                    ))}
                  </ul>
                </Detail>
                <Detail label="Analyzer">
                  {selected.analyzer}
                  {selected.model && (
                    <span className="text-muted-foreground"> · {selected.model.provider}/{selected.model.model}</span>
                  )}
                </Detail>
              </dl>

              <Button asChild variant="outline" size="sm">
                <Link to={videoLink(selected)}>Open in video</Link>
              </Button>

              <div className="space-y-3 border-t pt-4">
                {rejecting && (
                  <div className="space-y-2">
                    <Label htmlFor="reject-note">Reason for rejecting (required)</Label>
                    <Textarea
                      id="reject-note"
                      ref={noteRef}
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') setRejecting(false)
                        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) decide('rejected')
                      }}
                      placeholder="e.g. Legitimate criticism backed by public figures"
                    />
                    <p className="text-xs text-muted-foreground">
                      <Kbd>Ctrl</Kbd>+<Kbd>Enter</Kbd> to submit · <Kbd>Esc</Kbd> to cancel
                    </p>
                  </div>
                )}
                <div className="flex gap-2">
                  <Button onClick={() => decide('confirmed')}>
                    Confirm <Kbd>c</Kbd>
                  </Button>
                  <Button
                    variant="destructive"
                    disabled={rejecting && !note.trim()}
                    onClick={() => decide('rejected')}
                  >
                    {rejecting ? 'Submit reject' : 'Reject'} <Kbd>r</Kbd>
                  </Button>
                  <Button variant="outline" onClick={() => decide('needs_info')}>
                    Needs info <Kbd>n</Kbd>
                  </Button>
                </div>
              </div>

              {history.length > 0 && (
                <div className="space-y-2 border-t pt-4">
                  <h3 className="text-xs text-muted-foreground">Decisions</h3>
                  <ul className="space-y-1 text-sm">
                    {history.map((d) => (
                      <li key={d.at}>
                        <Badge variant={statusVariant[d.status]}>{d.status}</Badge>{' '}
                        <span className="text-muted-foreground">
                          {d.by} · {formatVnDateTime(d.at)}
                        </span>
                        {d.note && <p className="mt-1 pl-1 text-muted-foreground">“{d.note}”</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="p-6 text-center text-sm text-muted-foreground">Select a finding to review.</p>
          )}
        </section>
      </div>
    </div>
  )
}
