import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Checkbox } from '@/components/ui/checkbox'
import { collect, listJobs, type CollectLevel, type Job } from '@/api/jobs'
import { formatVnDateTime } from '@/lib/format'

type StepStatus = 'pending' | 'running' | 'done' | 'failed'

const statusVariant: Record<string, 'secondary' | 'default' | 'outline' | 'destructive'> = {
  queued: 'secondary',
  running: 'default',
  done: 'outline',
  failed: 'destructive',
}

const stepClass: Record<StepStatus, string> = {
  pending: 'text-muted-foreground',
  running: 'font-medium text-foreground',
  done: 'text-foreground line-through decoration-muted-foreground',
  failed: 'font-medium text-destructive',
}

// Ba bước lớn của job (SPEC 10.7). API cho biết bước đang chạy (`step`) và trạng thái chung.
const STEPS = ['collect', 'media', 'analyze']

function stepStatus(job: Job, i: number): StepStatus {
  if (job.status === 'done') return 'done'
  if (job.status === 'queued') return 'pending'
  const current = STEPS.indexOf(job.step ?? '')
  if (i < current) return 'done'
  if (i > current) return 'pending'
  return job.status === 'failed' ? 'failed' : 'running'
}

function Steps({ job }: { job: Job }) {
  const steps = STEPS.map((name, i) => ({ name, status: stepStatus(job, i) }))
  return (
    <div className="flex flex-wrap items-center gap-1 text-xs">
      {steps.map((s, i) => (
        <span key={s.name} className="flex items-center gap-1">
          {i > 0 && <span className="text-muted-foreground">→</span>}
          <span className={stepClass[s.status]}>{s.name}</span>
        </span>
      ))}
    </div>
  )
}

export default function CollectPage() {
  const { caseId = '' } = useParams()
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const [level, setLevel] = useState<CollectLevel>('full')
  const [force, setForce] = useState(false)

  const jobs = useQuery({
    queryKey: ['jobs', caseId],
    queryFn: () => listJobs(caseId),
    refetchInterval: 2000,
  })

  const create = useMutation({
    mutationFn: () => collect(caseId, input.trim(), level, force),
    onSuccess: () => {
      setInput('')
      setForce(false)
      queryClient.invalidateQueries({ queryKey: ['jobs', caseId] })
    },
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Collect</h1>

      <Card>
        <CardHeader>
          <CardTitle>New collection</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              if (input.trim()) create.mutate()
            }}
          >
            <div className="flex items-end gap-3">
              <div className="flex-1 space-y-2">
                <Label htmlFor="collect-input">Video link or ID</Label>
                <Input
                  id="collect-input"
                  placeholder="https://www.youtube.com/watch?v=…"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="collect-level">Level</Label>
                <Select value={level} onValueChange={(v) => setLevel(v as CollectLevel)}>
                  <SelectTrigger id="collect-level" className="w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="metadata">metadata</SelectItem>
                    <SelectItem value="text">text</SelectItem>
                    <SelectItem value="full">full</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button type="submit" disabled={!input.trim() || create.isPending}>
                {create.isPending ? 'Sending…' : 'Collect'}
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox id="collect-force" checked={force} onCheckedChange={(v) => setForce(v === true)} />
              <Label htmlFor="collect-force" className="font-normal text-muted-foreground">
                Collect again even if this video was collected in the last 10 minutes
              </Label>
            </div>
            {create.error && (
              <p role="alert" className="text-sm text-destructive">
                {create.error.message}
              </p>
            )}
          </form>
        </CardContent>
      </Card>

      <div className="space-y-2">
        <h2 className="text-lg font-semibold">Jobs</h2>
        {jobs.error && <p className="text-sm text-destructive">Could not load jobs: {jobs.error.message}</p>}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Input</TableHead>
              <TableHead>Level</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-40">Progress</TableHead>
              <TableHead>Steps</TableHead>
              <TableHead>Started</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.data?.map((job) => (
              <TableRow key={job.id} className="align-top">
                <TableCell className="max-w-80">
                  <div className="truncate font-mono text-xs">{job.target}</div>
                  {job.error && <p className="mt-1 text-xs whitespace-normal text-destructive">{job.error}</p>}
                </TableCell>
                <TableCell>{job.level}</TableCell>
                <TableCell>
                  <Badge variant={statusVariant[job.status] ?? 'outline'}>{job.status}</Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Progress value={job.progress} />
                    <span className="w-9 text-right text-xs text-muted-foreground">{job.progress}%</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Steps job={job} />
                </TableCell>
                <TableCell className="text-xs">{formatVnDateTime(job.created_at)}</TableCell>
              </TableRow>
            ))}
            {jobs.data?.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  No jobs yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
