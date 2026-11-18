import { XIcon } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// `id` gắn với <Label htmlFor> ở form cha.
// Danh sách chuỗi thêm/xoá được (biệt danh, viết tắt). Bỏ qua chuỗi rỗng và chuỗi trùng (không phân biệt hoa thường).
export default function TermListInput({
  id,
  values,
  placeholder,
  onChange,
}: {
  id: string
  values: string[]
  placeholder: string
  onChange: (values: string[]) => void
}) {
  const [draft, setDraft] = useState('')
  const term = draft.trim()
  const duplicate = values.some((v) => v.toLowerCase() === term.toLowerCase())

  function add() {
    if (!term || duplicate) return
    onChange([...values, term])
    setDraft('')
  }

  return (
    <div className="space-y-2">
      <div className="flex min-h-5 flex-wrap gap-1">
        {values.map((v) => (
          <Badge key={v} variant="secondary" className="h-6 pr-1">
            {v}
            <button
              type="button"
              className="rounded-sm opacity-60 hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={`Remove ${v}`}
              onClick={() => onChange(values.filter((x) => x !== v))}
            >
              <XIcon className="size-3" />
            </button>
          </Badge>
        ))}
        {values.length === 0 && <span className="text-sm text-muted-foreground">None yet.</span>}
      </div>
      <div className="flex gap-2">
        <Input
          id={id}
          placeholder={placeholder}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            // Enter thêm mục, không gửi form.
            if (e.key === 'Enter') {
              e.preventDefault()
              add()
            }
          }}
        />
        <Button type="button" variant="outline" onClick={add} disabled={!term || duplicate}>
          Add
        </Button>
      </div>
      {term && duplicate && <p className="text-xs text-muted-foreground">“{term}” is already in the list.</p>}
    </div>
  )
}
