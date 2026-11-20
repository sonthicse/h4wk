import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { listEntities } from '@/api/entities'
import { frameUrl, getTimeline, toVideoFinding } from '@/api/videos'
import { buildKeyframes } from '@/components/video/keyframes'
import { FrameImage } from '@/components/video/KeyframeStrip'
import { decide as postDecision, listQueue, type DecisionStatus, type QueueItem, type ReviewStatus } from '@/api/review'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { HoverHighlight, HoverItem } from '@/components/ui/hover-highlight'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { formatTime, inSpans, severityVariant } from '@/lib/findings'
import { formatVnDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'

// Hàng đợi và quyết định lấy từ API rà soát (T25); quyết định ghi vào reviews.jsonl ở backend.
type View = 'unreviewed' | 'needs_info' | 'all'

const statusVariant: Record<ReviewStatus, 'outline' | 'default' | 'secondary'> = {
  unreviewed: 'outline',
  confirmed: 'default',
  rejected: 'secondary',
  needs_info: 'outline',
}

function timeRange(item: QueueItem) {
  const f = item.finding
  return f.start == null ? '—' : `${formatTime(f.start)}–${formatTime(f.end ?? f.start)}`
}

// Mở trang Video detail tại đúng nghi vấn (trang tự nhảy tới start − 2s).
function videoLink(item: QueueItem) {
  const f = item.finding
  return `/videos/${encodeURIComponent(f.video_id)}?finding=${encodeURIComponent(f.id)}`
}

// Khung hình của nghi vấn ocr/visual/thumbnail kèm khung bao, dùng lại FrameImage của Video detail.
function FramePreview({ item, entityNames }: { item: QueueItem; entityNames: Record<string, string> }) {
  const f = item.finding
  const timeline = useQuery({
    queryKey: ['timeline', f.video_id, f.capture],
    queryFn: () => getTimeline(f.video_id, f.capture),
  })
  const vf = toVideoFinding(item)
  const frames = buildKeyframes(timeline.data, [vf], entityNames)
  const frame =
    frames.find((k) => k.id === vf.frame) ??
    frames.find((k) => inSpans(vf, k.t)) ??
    (vf.frame ? { id: vf.frame, t: vf.start ?? 0, ocr: [], faces: [], refImages: [], visual: null } : null)
  if (!frame) return null
  return <FrameImage frame={frame} src={frameUrl(f.video_id, frame.id, f.capture)} boxes className="w-full max-w-md" />
}

const views: { id: View; label: string }[] = [
  { id: 'unreviewed', label: 'Unreviewed' },
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
  const queryClient = useQueryClient()
  const queueQuery = useQuery({ queryKey: ['review-queue'], queryFn: () => listQueue() })
  const entities = useQuery({ queryKey: ['entities'], queryFn: listEntities })
  const entityName = (id: string) => entities.data?.find((e) => e.id === id)?.name ?? id
  const entityNames = Object.fromEntries((entities.data ?? []).map((e) => [e.id, e.name]))
  const [view, setView] = useState<View>('unreviewed')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [rejecting, setRejecting] = useState(false)
  const [note, setNote] = useState('')
  const noteRef = useRef<HTMLTextAreaElement>(null)

  // Backend đã sắp theo mức độ rồi thời gian.
  const all = queueQuery.data ?? []
  const queue = all.filter((it) => view === 'all' || it.status === view)
  const selected = queue.find((it) => it.finding.id === selectedId) ?? queue[0] ?? null
  const counts = {
    unreviewed: all.filter((it) => it.status === 'unreviewed').length,
    needs_info: all.filter((it) => it.status === 'needs_info').length,
    all: all.length,
  }

  const save = useMutation({
    mutationFn: ({ id, status, note }: { id: string; status: DecisionStatus; note: string }) => postDecision(id, status, note),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['review-queue'] }),
  })

  function select(it: QueueItem | undefined) {
    if (!it) return
    setSelectedId(it.finding.id)
    setRejecting(false)
    setNote('')
  }

  function move(step: number) {
    if (!selected) return
    select(queue[queue.indexOf(selected) + step])
  }

  function decide(status: DecisionStatus) {
    if (!selected || save.isPending) return
    if (status === 'rejected' && !note.trim()) {
      setRejecting(true)
      return
    }
    // Sang nghi vấn kế tiếp trong hàng đợi để duyệt liên tục không phải rời trang.
    const i = queue.indexOf(selected)
    const next = queue[i + 1] ?? (i > 0 ? queue[i - 1] : undefined)
    save.mutate(
      { id: selected.finding.id, status, note: note.trim() },
      {
        onSuccess: () => {
          setSelectedId(next?.finding.id ?? null)
          setRejecting(false)
          setNote('')
        },
      },
    )
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

  const history = selected?.decisions ?? []
  const f = selected?.finding

  return (
    <div className="flex flex-col gap-4 lg:h-[calc(100svh-3rem-3rem)]">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Review queue</h1>
        <p className="hidden items-center gap-1 md:flex text-xs text-muted-foreground">
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

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <HoverHighlight>
          <ul className="max-h-72 min-h-0 space-y-1 overflow-y-auto pr-1 lg:max-h-none">
            {queue.map((it) => (
              <HoverItem key={it.finding.id}>
                <button
                  type="button"
                  onClick={() => select(it)}
                  aria-current={selected === it ? 'true' : undefined}
                  className={cn(
                    'w-full rounded-md border p-3 text-left transition-colors',
                    selected === it && 'border-primary bg-muted',
                  )}
                >
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant={severityVariant[it.finding.severity]}>{it.finding.severity}</Badge>
                    <span>{it.finding.source_kind}</span>
                    <span className="font-mono">{timeRange(it)}</span>
                    <Badge variant={statusVariant[it.status]} className="ml-auto">{it.status}</Badge>
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm">{it.finding.quote}</p>
                  <p className="mt-1 truncate text-xs text-muted-foreground">{it.video.title ?? it.video.id}</p>
                </button>
              </HoverItem>
            ))}
            {queueQuery.isPending && <li className="p-6 text-center text-sm text-muted-foreground">Loading…</li>}
            {queueQuery.error && (
              <li className="p-6 text-center text-sm text-destructive">Could not load the queue: {queueQuery.error.message}</li>
            )}
            {queueQuery.data && queue.length === 0 && (
              <li className="p-6 text-center text-sm text-muted-foreground">Nothing left to review here.</li>
            )}
          </ul>
        </HoverHighlight>

        {/* key theo nghi vấn để panel cuộn lại về đầu mỗi khi chuyển nghi vấn. */}
        <section key={f?.id} className="min-h-0 overflow-y-auto rounded-md border p-4">
          {selected && f ? (
            <div className="space-y-4">
              <div>
                <h2 className="font-semibold">{selected.video.title ?? selected.video.id}</h2>
                <p className="text-sm text-muted-foreground">
                  {selected.video.channel && `${selected.video.channel} · `}
                  {f.source_kind} · {timeRange(selected)}
                </p>
              </div>

              {['ocr', 'visual', 'thumbnail'].includes(f.source_kind) && (
                <FramePreview item={selected} entityNames={entityNames} />
              )}

              <dl className="space-y-4">
                <Detail label="Quote">
                  <blockquote className="border-l-2 pl-3 italic">{f.quote}</blockquote>
                </Detail>
                <div className="flex flex-wrap gap-2">
                  <Badge variant={severityVariant[f.severity]}>{f.severity}</Badge>
                  <Badge variant="outline">{f.category}</Badge>
                  <Badge variant="outline">{f.confidence}</Badge>
                </div>
                <Detail label="Entity">{entityName(f.entity)}</Detail>
                <Detail label="Reason">{f.reason}</Detail>
                <Detail label="Triggers">
                  <ul className="space-y-1">
                    {(f.triggers ?? []).map((t, i) => (
                      <li key={i} className="font-mono text-xs">
                        {t.via}
                        {t.score != null && ` · score ${t.score.toFixed(2)}`}
                      </li>
                    ))}
                  </ul>
                </Detail>
                <Detail label="Analyzer">
                  {f.analyzer} {f.analyzer_version}
                  {f.model && (
                    <span className="text-muted-foreground"> · {f.model.provider}/{f.model.model}</span>
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
                {save.error && (
                  <p role="alert" className="text-sm text-destructive">
                    Could not save the decision: {save.error.message}
                  </p>
                )}
                <div className="flex gap-2">
                  <Button disabled={save.isPending} onClick={() => decide('confirmed')}>
                    Confirm <Kbd>c</Kbd>
                  </Button>
                  <Button
                    variant="destructive"
                    disabled={save.isPending || (rejecting && !note.trim())}
                    onClick={() => decide('rejected')}
                  >
                    {rejecting ? 'Submit reject' : 'Reject'} <Kbd>r</Kbd>
                  </Button>
                  <Button variant="outline" disabled={save.isPending} onClick={() => decide('needs_info')}>
                    Needs info <Kbd>n</Kbd>
                  </Button>
                </div>
              </div>

              {history.length > 0 && (
                <div className="space-y-2 border-t pt-4">
                  <h3 className="text-xs text-muted-foreground">Decisions</h3>
                  <ul className="space-y-1 text-sm">
                    {history.map((d) => (
                      <li key={`${d.at}-${d.status}`}>
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
