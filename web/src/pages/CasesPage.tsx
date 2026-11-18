import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { formatVnDateTime } from '@/lib/format'
import { createCase, listCases } from '@/mocks/data'

function NewCaseSheet({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [entities, setEntities] = useState('')

  const entityList = entities.split('\n').map((e) => e.trim()).filter(Boolean)
  const create = useMutation({
    mutationFn: () => createCase(name.trim(), entityList),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      setName('')
      setEntities('')
      onOpenChange(false)
    },
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[28rem] sm:max-w-md">
        <form
          className="flex h-full flex-col"
          onSubmit={(e) => {
            e.preventDefault()
            if (name.trim() && entityList.length > 0) create.mutate()
          }}
        >
          <SheetHeader>
            <SheetTitle>New case</SheetTitle>
            <SheetDescription>A case groups the videos and findings about the entities you monitor.</SheetDescription>
          </SheetHeader>
          <div className="space-y-4 px-4">
            <div className="space-y-2">
              <Label htmlFor="case-name">Name</Label>
              <Input id="case-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="case-entities">Entities (one per line)</Label>
              <Textarea
                id="case-entities"
                rows={4}
                value={entities}
                onChange={(e) => setEntities(e.target.value)}
                placeholder={'Nguyễn Văn A\nCông ty B'}
              />
            </div>
          </div>
          <SheetFooter>
            <Button type="submit" disabled={!name.trim() || entityList.length === 0 || create.isPending}>
              Create case
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  )
}

export default function CasesPage() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [creating, setCreating] = useState(false)
  const cases = useQuery({ queryKey: ['cases'], queryFn: listCases })

  const all = cases.data ?? []
  const query = q.trim().toLowerCase()
  const rows = all.filter((c) => !query || `${c.name} ${c.entities.join(' ')}`.toLowerCase().includes(query))
  const openFindings = all.reduce((sum, c) => sum + c.openFindings, 0)

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Cases</h1>
        <div className="flex gap-2 text-sm">
          <Badge variant="outline">{all.length} cases</Badge>
          <Badge variant="outline">{openFindings} open findings</Badge>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="w-64"
          aria-label="Search cases"
          placeholder="Search case or entity…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {q && (
          <Button variant="ghost" onClick={() => setQ('')}>
            Clear
          </Button>
        )}
        <span className="ml-auto text-sm text-muted-foreground">
          {rows.length} of {all.length}
        </span>
        <Button onClick={() => setCreating(true)}>New case</Button>
      </div>

      {cases.error && <p className="text-sm text-destructive">Could not load cases.</p>}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Entities</TableHead>
            <TableHead className="text-right">Videos</TableHead>
            <TableHead className="text-right">Open findings</TableHead>
            <TableHead>Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((c) => {
            const open = () => navigate(`/cases/${c.id}/dashboard`)
            return (
              <TableRow
                key={c.id}
                tabIndex={0}
                className="cursor-pointer focus-visible:bg-muted focus-visible:outline-none"
                onClick={open}
                onKeyDown={(e) => {
                  if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
                    e.preventDefault()
                    open()
                  }
                }}
              >
                <TableCell>
                  <Link
                    to={`/cases/${c.id}/dashboard`}
                    className="font-medium hover:underline"
                    tabIndex={-1}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {c.name}
                  </Link>
                </TableCell>
                <TableCell className="space-x-1">
                  {c.entities.map((e) => (
                    <Badge key={e} variant="secondary">{e}</Badge>
                  ))}
                </TableCell>
                <TableCell className="text-right">{c.videoCount}</TableCell>
                <TableCell className="text-right">{c.openFindings}</TableCell>
                <TableCell>{formatVnDateTime(c.updatedAt)}</TableCell>
              </TableRow>
            )
          })}
          {cases.data && rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground">
                {all.length === 0 ? 'No cases yet.' : 'No cases match this search.'}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <NewCaseSheet open={creating} onOpenChange={setCreating} />
    </div>
  )
}
