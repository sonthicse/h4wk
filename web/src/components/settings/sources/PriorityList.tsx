import { ArrowDown, ArrowUp, GripVertical, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { sourceLabel, type Cap, type SourceName } from '@/api/settings'

type Props = {
  cap: Cap
  order: SourceName[]
  enabled: Record<SourceName, boolean>
  paused: Record<SourceName, boolean>
  changed: boolean
  onChange: (order: SourceName[]) => void
}

function move(order: SourceName[], from: number, to: number) {
  const next = [...order]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}

export default function PriorityList({ cap, order, enabled, paused, changed, onChange }: Props) {

  const [dragFrom, setDragFrom] = useState<number | null>(null)
  const [dragOver, setDragOver] = useState<number | null>(null)
  const [announce, setAnnounce] = useState('')

  const isEmpty = order.length === 0
  const noSource = !isEmpty && order.every((name) => !enabled[name])
  const allPaused = !isEmpty && !noSource && order.filter((name) => enabled[name]).every((name) => paused[name])

  function moveBy(index: number, step: -1 | 1) {
    const name = order[index]
    onChange(move(order, index, index + step))
    setAnnounce(`${sourceLabel[name]} moved to position ${index + step + 1} for ${cap}.`)

    setTimeout(() => {
      const want = document.getElementById(`${cap}-${name}-${step < 0 ? 'up' : 'down'}`) as HTMLButtonElement | null
      const other = document.getElementById(`${cap}-${name}-${step < 0 ? 'down' : 'up'}`) as HTMLButtonElement | null
      ;(want && !want.disabled ? want : other)?.focus()
    })
  }

  return (
    <div className={cn('space-y-2 rounded-lg border p-3', noSource && 'border-destructive/50')}>
      <div className="flex items-center gap-2">
        <span className="font-mono text-sm font-medium">{cap}</span>
        {changed && <span className="text-xs text-muted-foreground">(changed)</span>}
      </div>

      <ol className="space-y-1">
        {order.map((name, i) => (
          <li
            key={name}
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData('text/plain', name)
              e.dataTransfer.effectAllowed = 'move'
              setDragFrom(i)
            }}
            onDragOver={(e) => {
              if (dragFrom === null) return
              e.preventDefault()
              setDragOver(i)
            }}
            onDragLeave={() => setDragOver((v) => (v === i ? null : v))}
            onDrop={(e) => {
              e.preventDefault()
              if (dragFrom !== null && dragFrom !== i) {
                onChange(move(order, dragFrom, i))
                setAnnounce(`${sourceLabel[order[dragFrom]]} moved to position ${i + 1} for ${cap}.`)
              }
              setDragFrom(null)
              setDragOver(null)
            }}
            onDragEnd={() => {
              setDragFrom(null)
              setDragOver(null)
            }}
            className={cn(
              'flex cursor-grab items-center gap-2 rounded-md border bg-background py-1 pr-1 pl-2 text-sm',
              dragFrom === i && 'opacity-50',
              dragOver === i && dragFrom !== i && 'border-primary ring-1 ring-primary',
            )}
          >
            <GripVertical className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            <span className="w-4 text-xs text-muted-foreground">{i + 1}.</span>
            <span className={cn('flex-1 truncate', !enabled[name] && 'text-muted-foreground line-through')}>
              {sourceLabel[name]}
            </span>
            {!enabled[name] && <Badge variant="outline">off</Badge>}
            {enabled[name] && paused[name] && <Badge variant="secondary">paused</Badge>}
            <Button
              id={`${cap}-${name}-up`}
              variant="ghost"
              size="icon-xs"
              aria-label={`Move ${sourceLabel[name]} up in ${cap}`}
              disabled={i === 0}
              onClick={() => moveBy(i, -1)}
            >
              <ArrowUp />
            </Button>
            <Button
              id={`${cap}-${name}-down`}
              variant="ghost"
              size="icon-xs"
              aria-label={`Move ${sourceLabel[name]} down in ${cap}`}
              disabled={i === order.length - 1}
              onClick={() => moveBy(i, 1)}
            >
              <ArrowDown />
            </Button>
          </li>
        ))}
      </ol>

      {isEmpty && (
        <p className="text-xs text-muted-foreground">Not set: all sources are tried in default order</p>
      )}
      {noSource && (
        <p className="flex items-start gap-1.5 text-xs text-destructive">
          <TriangleAlert className="mt-px size-3.5 shrink-0" aria-hidden />
          No enabled source. Collections will record this data type as no_source.
        </p>
      )}
      {allPaused && (
        <p className="text-xs text-muted-foreground">Every enabled source is paused right now.</p>
      )}
      <p className="sr-only" aria-live="polite">
        {announce}
      </p>
    </div>
  )
}
