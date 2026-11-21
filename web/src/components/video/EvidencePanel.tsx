import { useQuery } from '@tanstack/react-query'
import { getVerdict, type QueueItem } from '@/api/review'

type Kind = QueueItem['finding']['source_kind']

// Bằng chứng nhóm theo loại, theo thứ tự trong bản phác.
const groups: { label: string; kinds: Kind[] }[] = [
  { label: 'On-screen text', kinds: ['ocr', 'thumbnail'] },
  { label: 'Speech', kinds: ['speech'] },
  { label: 'Images', kinds: ['visual'] },
  { label: 'Comments', kinds: ['comment'] },
]

// Nghi vấn sớm nhất của nhóm; nghi vấn không có mốc thời gian xếp sau.
function earliest(list: QueueItem[]): QueueItem {
  return [...list].sort((a, b) => (a.finding.start ?? Infinity) - (b.finding.start ?? Infinity))[0]
}

// Bằng chứng của kết luận: số nghi vấn theo loại; bấm một dòng mở nghi vấn sớm nhất của loại đó.
// Không có kết luận thì không hiện gì.
export default function EvidencePanel({ videoId, items, onOpen }: { videoId: string; items: QueueItem[]; onOpen: (it: QueueItem) => void }) {
  const detail = useQuery({ queryKey: ['verdict', videoId], queryFn: () => getVerdict(videoId) })
  if (!detail.data?.verdict || items.length === 0) return null
  return (
    <section className="flex flex-col gap-2 rounded-md border p-3" aria-label="Evidence">
      <h2 className="text-sm font-medium">Evidence</h2>
      {groups.map((g) => {
        const list = items.filter((it) => g.kinds.includes(it.finding.source_kind))
        return (
          <button
            key={g.label}
            type="button"
            disabled={list.length === 0}
            onClick={() => onOpen(earliest(list))}
            className="flex justify-between rounded-md bg-muted/50 px-2 py-1.5 text-left text-sm hover:bg-muted disabled:pointer-events-none disabled:text-muted-foreground"
          >
            <span>{g.label}</span>
            <span className="font-semibold">{list.length}</span>
          </button>
        )
      })}
    </section>
  )
}
