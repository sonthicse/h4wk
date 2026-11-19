import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { createEntity, type Entity } from '@/api/entities'
import TermListInput from '@/components/entities/TermListInput'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

// Tạo đối tượng qua POST /api/entities. Backend chưa có API sửa đối tượng,
// nên biệt danh và viết tắt phải nhập ngay lúc tạo.
export default function NewEntityDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (entity: Entity) => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [aliases, setAliases] = useState<string[]>([])
  const [abbreviations, setAbbreviations] = useState<string[]>([])

  const create = useMutation({
    mutationFn: () => createEntity(name.trim(), aliases, abbreviations),
    onSuccess: async (entity) => {
      await queryClient.invalidateQueries({ queryKey: ['entities'] })
      setName('')
      setAliases([])
      setAbbreviations([])
      onOpenChange(false)
      onCreated(entity)
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault()
            if (name.trim()) create.mutate()
          }}
        >
          <DialogHeader>
            <DialogTitle>New entity</DialogTitle>
            <DialogDescription>A person or organisation to protect. Videos are analyzed for mentions of it.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="new-entity-name">Name</Label>
            <Input id="new-entity-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Nguyễn Văn A" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-entity-alias">Aliases</Label>
            <TermListInput id="new-entity-alias" values={aliases} placeholder="e.g. ông A" onChange={setAliases} />
            <p className="text-xs text-muted-foreground">
              Matched like the name: diacritics and case ignored, words of 4+ letters may have one typo.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-entity-abbr">Abbreviations</Label>
            <TermListInput id="new-entity-abbr" values={abbreviations} placeholder="e.g. NVA" onChange={setAbbreviations} />
            <p className="text-xs text-muted-foreground">Matched exactly, as a whole word.</p>
          </div>
          {create.error && (
            <p role="alert" className="text-sm text-destructive">
              Could not create the entity: {create.error.message}
            </p>
          )}
          <DialogFooter>
            <Button type="submit" disabled={!name.trim() || create.isPending}>
              {create.isPending ? 'Creating…' : 'Create entity'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
