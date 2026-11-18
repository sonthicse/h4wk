import { useEffect, useRef } from 'react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { formatVnDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { VideoComment } from '@/mocks/videos'

function CommentItem({
  comment,
  highlightId,
  findingHref,
  nested,
}: {
  comment: VideoComment
  highlightId: string | null
  findingHref: (findingId: string) => string
  nested?: boolean
}) {
  const ref = useRef<HTMLDivElement>(null)
  const highlighted = comment.findingId !== undefined && comment.findingId === highlightId

  // Mở bằng ?finding= của một comment thì cuộn tới comment đó.
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView({ block: 'center' })
  }, [highlighted])

  return (
    <div
      ref={ref}
      className={cn(
        'rounded-md border p-3 text-sm',
        nested && 'ml-8',
        comment.findingId && 'border-destructive/40 bg-destructive/5',
        highlighted && 'ring-2 ring-destructive',
      )}
    >
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">{comment.author}</span>
        <span>{formatVnDateTime(comment.publishedAt)}</span>
        <span>{comment.likeCount} likes</span>
        {comment.findingId && (
          <Link to={findingHref(comment.findingId)} className="ml-auto">
            <Badge variant="destructive">Flagged · view finding</Badge>
          </Link>
        )}
      </div>
      <p className="mt-1">{comment.text}</p>
    </div>
  )
}

// Comment và reply lồng một cấp (YouTube chỉ có hai cấp).
export default function CommentsTab({
  comments,
  highlightId,
  findingHref,
}: {
  comments: VideoComment[]
  highlightId: string | null
  findingHref: (findingId: string) => string
}) {
  if (comments.length === 0) return <p className="py-4 text-sm text-muted-foreground">No comments were collected.</p>

  const topLevel = comments.filter((c) => c.parentId === null)
  return (
    <div className="space-y-2 py-2">
      {topLevel.map((c) => (
        <div key={c.id} className="space-y-2">
          <CommentItem comment={c} highlightId={highlightId} findingHref={findingHref} />
          {comments
            .filter((r) => r.parentId === c.id)
            .map((r) => (
              <CommentItem key={r.id} comment={r} highlightId={highlightId} findingHref={findingHref} nested />
            ))}
        </div>
      ))}
    </div>
  )
}
