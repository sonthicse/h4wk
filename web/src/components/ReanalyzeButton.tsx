import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router'
import { reanalyze } from '@/api/jobs'
import { LoaderCircleIcon } from '@/components/animate-ui/icons/loader-circle'
import { Button } from '@/components/ui/button'

export default function ReanalyzeButton({ videoIds, label }: { videoIds?: string[]; label: string }) {
  const queryClient = useQueryClient()
  const run = useMutation({
    mutationFn: () => reanalyze(videoIds),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  })
  return (
    <span className="inline-flex flex-wrap items-center gap-2 text-sm">
      <Button variant="outline" disabled={run.isPending} onClick={() => run.mutate()}>
        {run.isPending && <LoaderCircleIcon animate />}
        {label}
      </Button>
      {run.data && (
        <span role="status" className="text-muted-foreground">
          {run.data.length === 0 ? (
            'No processed videos yet.'
          ) : (
            <>
              {run.data.length} {run.data.length === 1 ? 'job' : 'jobs'} queued.{' '}
              <Link to="/collect" className="underline">
                See progress
              </Link>
            </>
          )}
        </span>
      )}
      {run.isError && (
        <span role="alert" className="text-destructive">
          {run.error.message}
        </span>
      )}
    </span>
  )
}
