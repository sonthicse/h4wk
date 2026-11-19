import { useEffect, useRef } from 'react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { formatVnDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { VideoComment } from '@/api/videos'

function CommentItem({
  comment,
  findingId,
  highlightId,
  findingHref,
  nested,
}: {
  comment: VideoComment
  findingId: string | undefined
  highlightId: string | null
  findingHref: (findingId: string) => string
  nested?: boolean
}) {
  const ref = useRef<HTMLDivElement>(null)
  const highlighted = findingId !== undefined && findingId === highlightId

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
        findingId && 'border-destructive/40 bg-destructive/5',
        highlighted && 'ring-2 ring-destructive',
      )}
    >
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">{comment.author_channel_id ?? 'Unknown author'}</span>
        {comment.published_at && <span>{formatVnDateTime(comment.published_at)}</span>}
        <span>{comment.like_count ?? 0} likes</span>
        {findingId && (
          <Link to={findingHref(findingId)} className="ml-auto">
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
  findingByComment,
  highlightId,
  findingHref,
}: {
  comments: VideoComment[]
  findingByComment: Map<string, string> // comment_id -> id nghi vấn
  highlightId: string | null
  findingHref: (findingId: string) => string
}) {
  if (comments.length === 0) return <p className="py-4 text-sm text-muted-foreground">No comments were collected.</p>

  // Reply mà không thấy comment cha trong danh sách thì coi như comment gốc để không bị mất.
  const ids = new Set(comments.map((c) => c.id))
  const topLevel = comments.filter((c) => !c.parent_id || !ids.has(c.parent_id))
  return (
    <div className="space-y-2 py-2">
      {topLevel.map((c) => (
        <div key={c.id} className="space-y-2">
          <CommentItem comment={c} findingId={findingByComment.get(c.id)} highlightId={highlightId} findingHref={findingHref} />
          {comments
            .filter((r) => r.parent_id === c.id)
            .map((r) => (
              <CommentItem key={r.id} comment={r} findingId={findingByComment.get(r.id)} highlightId={highlightId} findingHref={findingHref} nested />
            ))}
        </div>
      ))}
    </div>
  )
}
