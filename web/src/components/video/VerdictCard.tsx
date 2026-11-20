import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { ApiError } from '@/api/client'
import { decideVideo, getVerdict, type QueueItem, type VideoDecisionStatus } from '@/api/review'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { formatTime, severityVariant, statusVariant } from '@/lib/findings'
import { formatVnDateTime } from '@/lib/format'

type Kind = QueueItem['finding']['source_kind']

// Bằng chứng nhóm theo loại, theo thứ tự hiển thị.
const groups: { label: string; kinds: Kind[] }[] = [
  { label: 'On-screen text', kinds: ['ocr', 'thumbnail'] },
  { label: 'Speech', kinds: ['speech'] },
  { label: 'Comments', kinds: ['comment'] },
  { label: 'Visual', kinds: ['visual'] },
]

function Kbd({ children }: { children: React.ReactNode }) {
  return <kbd className="rounded border bg-muted px-1.5 font-mono text-[10px] text-muted-foreground">{children}</kbd>
}

// Thẻ kết luận của video, nút duyệt cả video và bằng chứng. Không có kết luận thì không hiện gì.
export default function VerdictCard({ videoId, items, onOpen }: { videoId: string; items: QueueItem[]; onOpen: (it: QueueItem) => void }) {
  const queryClient = useQueryClient()
  const detail = useQuery({ queryKey: ['verdict', videoId], queryFn: () => getVerdict(videoId) })
  const [rejecting, setRejecting] = useState(false)
  const [note, setNote] = useState('')
  const noteRef = useRef<HTMLTextAreaElement>(null)

  const save = useMutation({
    mutationFn: ({ runId, status, note }: { runId: string; status: VideoDecisionStatus; note: string }) =>
      decideVideo(videoId, runId, status, note),
    onSuccess: () => {
      setRejecting(false)
      setNote('')
    },
    onSettled: (_d, err) => {
      // 409: kết luận đã đổi, tải lại để lấy run mới.
      queryClient.invalidateQueries({ queryKey: ['verdict', videoId] })
      queryClient.invalidateQueries({ queryKey: ['review-videos'] })
      if (err) setRejecting(false)
    },
  })

  const data = detail.data
  const verdict = data?.verdict

  function decide(status: VideoDecisionStatus) {
    if (!verdict || save.isPending) return
    if (status === 'rejected' && !note.trim()) {
      setRejecting(true)
      return
    }
    save.mutate({ runId: verdict.run_id, status, note: note.trim() })
  }

  useEffect(() => {
    if (rejecting) noteRef.current?.focus()
  }, [rejecting])

  // Phím tắt c/r/n như hàng đợi; bỏ qua khi đang gõ chữ.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement
      if (target.closest('input, textarea, [role="combobox"]') || e.ctrlKey || e.metaKey || e.altKey) return
      const actions: Record<string, () => void> = {
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

  if (!data || !verdict) return null
  const basis = new Set(verdict.finding_ids)
  const last = data.decisions[0]
  const conflict = save.error instanceof ApiError && save.error.status === 409

  return (
    <section className="space-y-4 rounded-md border p-4" aria-label="Verdict">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="font-semibold">Verdict</h2>
        <Badge variant={verdict.violation === 'yes' ? 'destructive' : 'outline'}>{verdict.violation}</Badge>
        {verdict.severity && <Badge variant={severityVariant[verdict.severity]}>{verdict.severity}</Badge>}
        <Badge variant="outline">{verdict.confidence}</Badge>
        {verdict.categories.map((c) => (
          <Badge key={c} variant="outline">{c}</Badge>
        ))}
        <Badge variant={statusVariant[data.status]} className="ml-auto">{data.status}</Badge>
      </div>
      {verdict.summary && <p className="text-sm">{verdict.summary}</p>}
      {last && (
        <p className="text-xs text-muted-foreground">
          Last decision: {last.status} by {last.by} · {formatVnDateTime(last.at)}
          {last.note && ` · “${last.note}”`}
        </p>
      )}

      <div className="space-y-2">
        {rejecting && (
          <div className="space-y-2">
            <Label htmlFor="verdict-note">Reason for rejecting (required)</Label>
            <Textarea
              id="verdict-note"
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
            {conflict ? 'Verdict changed, reload.' : `Could not save the decision: ${save.error.message}`}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button disabled={save.isPending} onClick={() => decide('confirmed')}>
            Confirm <Kbd>c</Kbd>
          </Button>
          <Button variant="destructive" disabled={save.isPending || (rejecting && !note.trim())} onClick={() => decide('rejected')}>
            {rejecting ? 'Submit reject' : 'Reject'} <Kbd>r</Kbd>
          </Button>
          <Button variant="outline" disabled={save.isPending} onClick={() => decide('needs_info')}>
            Needs info <Kbd>n</Kbd>
          </Button>
        </div>
      </div>

      {items.length > 0 && (
        <div className="space-y-3 border-t pt-3">
          <h3 className="text-xs text-muted-foreground">Evidence</h3>
          {groups.map((g) => {
            const list = items.filter((it) => g.kinds.includes(it.finding.source_kind))
            if (list.length === 0) return null
            return (
              <div key={g.label} className="space-y-1">
                <h4 className="text-sm font-medium">{g.label}</h4>
                <ul className="space-y-1">
                  {list.map((it) => {
                    const f = it.finding
                    return (
                      <li key={f.id}>
                        <button
                          type="button"
                          onClick={() => onOpen(it)}
                          className="flex w-full items-start gap-2 rounded px-2 py-1 text-left text-sm hover:bg-muted"
                        >
                          <span className="w-12 shrink-0 font-mono text-xs text-muted-foreground">{f.start != null ? formatTime(f.start) : '—'}</span>
                          <span className="line-clamp-2 min-w-0 flex-1">{f.quote}</span>
                          <Badge variant="outline" className="shrink-0">{f.category}</Badge>
                          {basis.has(f.id) && <Badge className="shrink-0">basis</Badge>}
                        </button>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
