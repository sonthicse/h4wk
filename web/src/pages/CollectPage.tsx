import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
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
import { addWatchItem, isChannelInput } from '@/api/watchlist'
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

// Các bước con của job theo mức thu (backend jobs/pipeline.py). API cho biết bước đang chạy (`step`)
// và trạng thái chung. Bước "media" là lúc chuẩn bị, ngay trước bước con đầu tiên sau collect.
const STEPS_BY_LEVEL: Record<string, string[]> = {
  full: ['collect', 'transcribe', 'frames', 'ocr', 'vlm', 'analyze'],
  text: ['collect', 'ocr', 'vlm', 'analyze'],
  metadata: ['collect', 'analyze'],
}

function stepsOf(job: Job) {
  return STEPS_BY_LEVEL[job.level] ?? STEPS_BY_LEVEL.full
}

function stepStatus(job: Job, steps: string[], i: number): StepStatus {
  if (job.status === 'done') return 'done'
  if (job.status === 'queued' && !job.step) return 'pending'
  const current = job.step === 'media' ? 1 : steps.indexOf(job.step ?? '')
  // Job đang chờ ở hàng đợi kế tiếp: `step` là bước sắp chạy, các bước trước đã xong.
  if (job.status === 'queued') return i < current ? 'done' : 'pending'
  if (i < current) return 'done'
  if (i > current) return 'pending'
  return job.status === 'failed' ? 'failed' : 'running'
}

function Steps({ job }: { job: Job }) {
  const names = stepsOf(job)
  const steps = names.map((name, i) => ({ name, status: stepStatus(job, names, i) }))
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
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const [level, setLevel] = useState<CollectLevel>('full')
  const [force, setForce] = useState(false)

  const jobs = useQuery({
    queryKey: ['jobs'],
    queryFn: listJobs,
    refetchInterval: 2000,
  })

  const [channelAdded, setChannelAdded] = useState(false)
  const [queuedCount, setQueuedCount] = useState(0) // số job vừa tạo từ link playlist

  // Link kênh đi vào watchlist (kênh tự thu 10 video mới nhất); link video tạo job collect như cũ.
  const create = useMutation({
    mutationFn: async () => {
      const channel = isChannelInput(input)
      if (channel) {
        await addWatchItem(input, level)
        return { channel, jobs: 0 }
      }
      const jobs = await collect(input.trim(), level, force)
      return { channel, jobs: jobs.length }
    },
    onSuccess: ({ channel, jobs }) => {
      setInput('')
      setForce(false)
      setChannelAdded(channel)
      setQueuedCount(jobs)
      queryClient.invalidateQueries({ queryKey: [channel ? 'watchlist' : 'jobs'] })
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
              setChannelAdded(false)
              if (input.trim()) create.mutate()
            }}
          >
            <div className="flex items-end gap-3">
              <div className="flex-1 space-y-2">
                <Label htmlFor="collect-input">Video, playlist or channel link</Label>
                <Input
                  id="collect-input"
                  placeholder="https://www.youtube.com/watch?v=…, a playlist link, or a channel link / @handle"
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
            {queuedCount > 1 && (
              <p role="status" className="text-sm text-muted-foreground">
                Queued {queuedCount} videos from the playlist.
              </p>
            )}
            {channelAdded && (
              <p role="status" className="text-sm text-muted-foreground">
                Channel added to the watchlist.{' '}
                <Link to="/watchlist" className="underline">
                  Open Watchlist
                </Link>
              </p>
            )}
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
                  {/* Bước VLM/OCR cần nhà cung cấp AI có key; backend báo "no AI provider available" khi thiếu. */}
                  {job.error?.includes('no AI provider available') && (
                    <p className="mt-1 text-xs">
                      <Link to="/settings/ai" className="underline">
                        Add an AI provider key in Settings
                      </Link>
                      , or collect at the <span className="font-mono">metadata</span> level.
                    </p>
                  )}
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
