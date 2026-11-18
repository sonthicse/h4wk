import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { addEntity, createCase, getCase, listCases } from '@/api/cases'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { formatVnDateTime } from '@/lib/format'

function NewCaseSheet({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [goal, setGoal] = useState('')
  const [entities, setEntities] = useState('')

  const entityList = entities.split('\n').map((e) => e.trim()).filter(Boolean)
  // Tạo case rồi thêm từng đối tượng; API chưa có lệnh tạo case kèm đối tượng trong một lần gọi.
  const create = useMutation({
    mutationFn: async () => {
      const c = await createCase(title.trim(), goal.trim())
      for (const name of entityList) await addEntity(c.id, name)
      return c
    },
    onSuccess: (c) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      setTitle('')
      setGoal('')
      setEntities('')
      onOpenChange(false)
      navigate(`/cases/${c.id}/collect`)
    },
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[28rem] sm:max-w-md">
        <form
          className="flex h-full flex-col"
          onSubmit={(e) => {
            e.preventDefault()
            if (title.trim() && entityList.length > 0) create.mutate()
          }}
        >
          <SheetHeader>
            <SheetTitle>New case</SheetTitle>
            <SheetDescription>A case groups the videos and findings about the entities you monitor.</SheetDescription>
          </SheetHeader>
          <div className="space-y-4 px-4">
            <div className="space-y-2">
              <Label htmlFor="case-title">Title</Label>
              <Input id="case-title" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="case-goal">Goal (optional)</Label>
              <Input id="case-goal" value={goal} onChange={(e) => setGoal(e.target.value)} />
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
            {create.error && (
              <p role="alert" className="text-sm text-destructive">
                Could not create the case: {create.error.message}
              </p>
            )}
          </div>
          <SheetFooter>
            <Button type="submit" disabled={!title.trim() || entityList.length === 0 || create.isPending}>
              {create.isPending ? 'Creating…' : 'Create case'}
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

  // Danh sách chỉ có id và tiêu đề; đối tượng, người tạo và ngày tạo lấy từ chi tiết từng case.
  const details = useQueries({
    queries: (cases.data ?? []).map((c) => ({ queryKey: ['case', c.id], queryFn: () => getCase(c.id) })),
  })

  const all = (cases.data ?? []).map((c, i) => ({ ...c, detail: details[i]?.data }))
  const query = q.trim().toLowerCase()
  const rows = all.filter(
    (c) => !query || `${c.title} ${c.detail?.entities.map((e) => e.name).join(' ') ?? ''}`.toLowerCase().includes(query),
  )

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Cases</h1>
        <Badge variant="outline">
          {all.length} {all.length === 1 ? 'case' : 'cases'}
        </Badge>
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

      {cases.error && <p className="text-sm text-destructive">Could not load cases: {cases.error.message}</p>}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Title</TableHead>
            <TableHead>Entities</TableHead>
            <TableHead>Owner</TableHead>
            <TableHead>Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((c) => {
            const open = () => navigate(`/cases/${c.id}/collect`)
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
                    to={`/cases/${c.id}/collect`}
                    className="font-medium hover:underline"
                    tabIndex={-1}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {c.title}
                  </Link>
                  <p className="font-mono text-xs text-muted-foreground">{c.id}</p>
                </TableCell>
                <TableCell className="space-x-1">
                  {c.detail?.entities.map((e) => (
                    <Badge key={e.id} variant="secondary">{e.name}</Badge>
                  ))}
                </TableCell>
                <TableCell className="font-mono text-xs">{c.detail?.owner}</TableCell>
                <TableCell>{c.detail && formatVnDateTime(c.detail.created_at)}</TableCell>
              </TableRow>
            )
          })}
          {cases.isPending && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                Loading…
              </TableCell>
            </TableRow>
          )}
          {cases.data && rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                {all.length === 0 ? 'No cases yet. Create one to start collecting.' : 'No cases match this search.'}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <NewCaseSheet open={creating} onOpenChange={setCreating} />
    </div>
  )
}
