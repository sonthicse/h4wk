import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { updateEntity, type Entity } from '@/api/entities'
import TermListInput from '@/components/entities/TermListInput'

type Form = { name: string; aliases: string[]; abbreviations: string[] }

// Form sửa tên, biệt danh, viết tắt. Trang cha đặt `key` theo id đối tượng để form khởi tạo lại khi đổi đối tượng.
export default function EntityForm({ entity }: { entity: Entity }) {
  const queryClient = useQueryClient()
  const initial: Form = { name: entity.name, aliases: entity.aliases, abbreviations: entity.abbreviations }
  const [form, setForm] = useState<Form>(initial)

  const save = useMutation({
    mutationFn: () => updateEntity(entity.id, { ...form, name: form.name.trim() }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['entities'] }),
  })

  const dirty = JSON.stringify(form) !== JSON.stringify(initial)
  const set = <K extends keyof Form>(key: K) => (value: Form[K]) => setForm((f) => ({ ...f, [key]: value }))

  return (
    <form
      className="space-y-5"
      onSubmit={(e) => {
        e.preventDefault()
        if (dirty && form.name.trim()) save.mutate()
      }}
    >
      <div className="space-y-2">
        <Label htmlFor="entity-name">Name</Label>
        <Input id="entity-name" className="max-w-md" value={form.name} onChange={(e) => set('name')(e.target.value)} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-2">
          <Label htmlFor="entity-alias">Aliases</Label>
          <TermListInput id="entity-alias" values={form.aliases} placeholder="e.g. ông A" onChange={set('aliases')} />
          <p className="text-xs text-muted-foreground">
            Matched like the name: diacritics and case ignored, words of 4+ letters may have one typo.
          </p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="entity-abbr">Abbreviations</Label>
          <TermListInput id="entity-abbr" values={form.abbreviations} placeholder="e.g. NVA" onChange={set('abbreviations')} />
          <p className="text-xs text-muted-foreground">Matched exactly, as a whole word.</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button type="submit" disabled={!dirty || !form.name.trim() || save.isPending}>
          {save.isPending ? 'Saving…' : 'Save changes'}
        </Button>
        {dirty && (
          <Button type="button" variant="ghost" onClick={() => setForm(initial)}>
            Discard
          </Button>
        )}
        {!form.name.trim() && <span className="text-sm text-destructive">Name is required.</span>}
        {save.error && <span className="text-sm text-destructive">Could not save changes: {save.error.message}</span>}
        {save.isSuccess && !dirty && <span className="text-sm text-muted-foreground">Saved.</span>}
      </div>
    </form>
  )
}
