import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { createEntity, type Entity } from '@/mocks/entities'

export default function NewEntityDialog({
  caseId,
  open,
  onOpenChange,
  onCreated,
}: {
  caseId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (entity: Entity) => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')

  const create = useMutation({
    mutationFn: () => createEntity(caseId, name.trim()),
    onSuccess: async (entity) => {
      await queryClient.invalidateQueries({ queryKey: ['entities', caseId] })
      setName('')
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
            <DialogDescription>
              A person or organisation to protect in this case. Add aliases and reference images after creating it.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="new-entity-name">Name</Label>
            <Input id="new-entity-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Nguyễn Văn A" />
          </div>
          {create.isError && <p className="text-sm text-destructive">Could not create the entity.</p>}
          <DialogFooter>
            <Button type="submit" disabled={!name.trim() || create.isPending}>
              Create entity
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
