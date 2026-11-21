import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { LoaderCircleIcon } from '@/components/animate-ui/icons/loader-circle'
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

// Theo bản phác: done nền đậm, running viền đậm, failed đỏ, queued viền nhạt.
const statusVariant: Record<string, 'secondary' | 'default' | 'outline' | 'destructive'> = {
  queued: 'outline',
  running: 'outline',
  done: 'default',
  failed: 'destructive',
}

// Mỗi bước là một chip: xong nền nhạt, đang chạy nền đậm, lỗi đỏ, chưa chạy viền đứt.
const stepClass: Record<StepStatus, string> = {
  pending: 'border border-dashed text-muted-foreground',
  running: 'bg-primary text-primary-foreground',
  done: 'bg-muted text-foreground/80',
  failed: 'bg-destructive/10 text-destructive',
}

// Các bước con của job theo mức thu (backend jobs/pipeline.py). API cho biết bước đang chạy (`step`)
// và trạng thái chung. Bước "media" là lúc chuẩn bị, ngay trước bước con đầu tiên sau collect.
// Bước match có từ T40; job cũ hoặc job bị bỏ qua bước match vẫn hiện done.
const STEPS_BY_LEVEL: Record<string, string[]> = {
  full: ['collect', 'transcribe', 'frames', 'ocr', 'match', 'analyze'],
  text: ['collect', 'ocr', 'match', 'analyze'],
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
    <div className="flex flex-wrap gap-1 text-[11px]">
      {steps.map((s) => (
        <span key={s.name} className={`rounded-md px-1.5 py-px ${stepClass[s.status]}`}>
          {s.name}
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
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
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
                {create.isPending && <LoaderCircleIcon animate />}
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
                  <div className="truncate font-mono text-xs" title={job.target}>
                    {job.video_id || job.target}
                  </div>
                  {job.error && <p className="mt-1 text-xs whitespace-normal text-destructive">{job.error}</p>}
                </TableCell>
                <TableCell>{job.level}</TableCell>
                <TableCell>
                  <Badge
                    variant={statusVariant[job.status] ?? 'outline'}
                    className={job.status === 'running' ? 'border-foreground' : job.status === 'queued' ? 'text-muted-foreground' : undefined}
                  >
                    {job.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Progress value={job.progress} aria-label={`${job.progress}%`} />
                </TableCell>
                <TableCell>
                  <Steps job={job} />
                </TableCell>
                <TableCell className="text-xs">{formatVnDateTime(job.created_at)}</TableCell>
              </TableRow>
            ))}
            {jobs.data?.length === 0 && (
              <TableRow highlight={false}>
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
