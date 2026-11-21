import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getVerdict, type QueueItem } from '@/api/review'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatTime, mergeKey } from '@/lib/findings'

type Kind = QueueItem['finding']['source_kind']

// Bằng chứng nhóm theo loại, theo thứ tự hiển thị.
const groups: { label: string; kinds: Kind[] }[] = [
  { label: 'On-screen text', kinds: ['ocr', 'thumbnail'] },
  { label: 'Speech', kinds: ['speech'] },
  { label: 'Comments', kinds: ['comment'] },
  { label: 'Visual', kinds: ['visual'] },
]

const MAX_ROWS = 5
const sevRank: Record<string, number> = { high: 0, medium: 1, low: 2 }

type Row = { key: string; text: string; first: QueueItem; count: number; from: number | null; to: number | null; basis: boolean }

// Gộp các nghi vấn có cùng khoá bỏ dấu thành một dòng.
function mergeRows(list: QueueItem[], basis: Set<string>): Row[] {
  const map = new Map<string, Row>()
  const variants = new Map<string, Map<string, number>>()
  for (const it of list) {
    const f = it.finding
    const key = mergeKey(f.quote)
    const t = f.start ?? null
    const row = map.get(key)
    variants.get(key)?.set(f.quote, (variants.get(key)?.get(f.quote) ?? 0) + 1)
    if (!row) {
      variants.set(key, new Map([[f.quote, 1]]))
      map.set(key, { key, text: f.quote, first: it, count: 1, from: t, to: t, basis: basis.has(f.id) })
      continue
    }
    row.count++
    row.basis ||= basis.has(f.id)
    if (t !== null) {
      if (row.from === null || t < row.from) {
        row.from = t
        row.first = it
      }
      if (row.to === null || t > row.to) row.to = t
    }
  }
  // Dòng gộp hiện bản gốc xuất hiện nhiều nhất.
  for (const [key, row] of map) row.text = [...variants.get(key)!].sort((a, b) => b[1] - a[1])[0][0]
  return [...map.values()].sort(
    (a, b) =>
      Number(b.basis) - Number(a.basis) ||
      (sevRank[a.first.finding.severity] ?? 3) - (sevRank[b.first.finding.severity] ?? 3) ||
      (a.from ?? 0) - (b.from ?? 0),
  )
}

function Group({ label, rows, onOpen, total }: { label: string; rows: Row[]; total: number; onOpen: (it: QueueItem) => void }) {
  const [all, setAll] = useState(false)
  const shown = all ? rows : rows.slice(0, MAX_ROWS)
  return (
    <div className="space-y-1">
      <h4 className="text-sm font-medium">
        {label} ({total})
      </h4>
      <ul className="space-y-1">
        {shown.map((r) => {
          const f = r.first.finding
          return (
            <li key={r.key}>
              <button
                type="button"
                onClick={() => onOpen(r.first)}
                className="flex w-full items-start gap-2 rounded px-2 py-1 text-left text-sm hover:bg-muted"
              >
                <span className="w-32 shrink-0 whitespace-nowrap font-mono text-xs text-muted-foreground">
                  {r.count > 1 && `×${r.count} · `}
                  {r.from != null ? formatTime(r.from) : '—'}
                  {r.count > 1 && r.to != null && r.to !== r.from && `–${formatTime(r.to)}`}
                </span>
                <span className="line-clamp-2 min-w-0 flex-1">{r.text}</span>
                <Badge variant="outline" className="shrink-0">{f.category}</Badge>
                {r.basis && <Badge className="shrink-0">basis</Badge>}
              </button>
            </li>
          )
        })}
      </ul>
      {rows.length > MAX_ROWS && (
        <Button variant="ghost" size="sm" onClick={() => setAll(!all)}>
          {all ? 'Show less' : `Show all (${rows.length})`}
        </Button>
      )}
    </div>
  )
}

// Bằng chứng của kết luận, đặt dưới trình phát. Không có kết luận thì không hiện gì.
export default function EvidencePanel({ videoId, items, onOpen }: { videoId: string; items: QueueItem[]; onOpen: (it: QueueItem) => void }) {
  const detail = useQuery({ queryKey: ['verdict', videoId], queryFn: () => getVerdict(videoId) })
  const verdict = detail.data?.verdict
  if (!verdict || items.length === 0) return null
  const basis = new Set(verdict.finding_ids)
  return (
    <section className="space-y-3 rounded-md border p-4" aria-label="Evidence">
      <h3 className="text-xs text-muted-foreground">Evidence</h3>
      {groups.map((g) => {
        const list = items.filter((it) => g.kinds.includes(it.finding.source_kind))
        if (list.length === 0) return null
        return <Group key={g.label} label={g.label} total={list.length} rows={mergeRows(list, basis)} onOpen={onOpen} />
      })}
    </section>
  )
}
