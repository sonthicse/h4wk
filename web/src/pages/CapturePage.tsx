import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import FilesTable from '@/components/capture/FilesTable'
import ManifestCard from '@/components/capture/ManifestCard'
import SourcesTable from '@/components/capture/SourcesTable'
import { Badge } from '@/components/ui/badge'
import { getCapture, getVideo } from '@/api/videos'

export default function CapturePage() {
  const { videoId = '', captureId = '' } = useParams()
  const capture = useQuery({
    queryKey: ['capture', videoId, captureId],
    queryFn: () => getCapture(videoId, captureId),
  })
  // Chỉ để lấy tiêu đề; lỗi hay không có thì hiện mã video.
  const video = useQuery({ queryKey: ['video', videoId], queryFn: () => getVideo(videoId) })
  const videoUrl = `/videos/${videoId}`

  if (capture.isLoading) return <p className="text-sm text-muted-foreground">Loading capture…</p>
  if (capture.error) return <p className="text-sm text-destructive">Could not load capture.</p>

  const c = capture.data
  if (!c) {
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Capture not found</h1>
        <p className="text-sm text-muted-foreground">
          There is no capture <code>{captureId}</code> for video <code>{videoId}</code>.
        </p>
        <Link className="text-sm underline" to={videoUrl}>
          Back to video
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <Link className="text-sm text-muted-foreground underline" to={videoUrl}>
            ← Back to video
          </Link>
          <h1 className="text-2xl font-semibold">{video.data?.video.title ?? videoId}</h1>
        </div>
        <div className="flex gap-2 text-sm">
          <Badge variant="outline">
            <code>{captureId}</code>
          </Badge>
          <Badge variant="outline">{c.manifest.level}</Badge>
        </div>
      </div>
      <ManifestCard manifest={c.manifest} />
      <SourcesTable sources={c.manifest.sources} />
      <FilesTable videoId={videoId} captureId={captureId} capture={c} />
    </div>
  )
}
