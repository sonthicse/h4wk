import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { ApiError } from '@/api/client'
import { decideVideo, getVerdict, type VideoDecisionStatus } from '@/api/review'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { severityVariant, statusVariant } from '@/lib/findings'
import { formatVnDateTime } from '@/lib/format'

function Kbd({ children }: { children: React.ReactNode }) {
  return <kbd className="rounded border bg-muted px-1.5 font-mono text-[10px] text-muted-foreground">{children}</kbd>
}

export default function VerdictCard({ videoId }: { videoId: string }) {
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

    </section>
  )
}
