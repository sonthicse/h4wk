import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatVnDateTime } from '@/lib/format'
import type { Manifest } from '@/api/videos'

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-4 py-1.5 text-sm">
      <dt className="w-32 shrink-0 text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-all">{children}</dd>
    </div>
  )
}

export default function ManifestCard({ manifest }: { manifest: Manifest }) {
  const { trigger } = manifest
  return (
    <Card>
      <CardHeader>
        <CardTitle>Manifest</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-8">
          <div>
            <Row label="Schema">
              <code>{manifest.schema}</code>
            </Row>
            <Row label="Source URL">
              <a className="underline" href={manifest.source_url} target="_blank" rel="noreferrer">
                {manifest.source_url}
              </a>
            </Row>
            <Row label="Collected at">{formatVnDateTime(manifest.collected_at)} (GMT+7)</Row>
            <Row label="Collector">
              <code>{manifest.collector}</code>
            </Row>
          </div>
          <div>
            <Row label="Trigger">
              <Badge variant="outline">{trigger.type}</Badge>
              {trigger.watch_item && <span className="ml-2 text-muted-foreground">{trigger.watch_item}</span>}
              {trigger.event && <span className="ml-2 text-muted-foreground">({trigger.event})</span>}
            </Row>
            <Row label="Level">
              <Badge variant="outline">{manifest.level}</Badge>
            </Row>
            <Row label="Tool version">{manifest.tool_version}</Row>
            <Row label="Previous capture">
              {manifest.previous_capture ? <code>{manifest.previous_capture}</code> : <span className="text-muted-foreground">none</span>}
            </Row>
          </div>
        </dl>
      </CardContent>
    </Card>
  )
}
