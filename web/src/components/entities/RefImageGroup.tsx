import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2Icon, UploadIcon } from 'lucide-react'
import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import RefThumb from '@/components/entities/RefThumb'
import { formatVnDateTime } from '@/lib/format'
import type { Entity } from '@/api/entities'
import { addRefImages, deleteRefImage, type RefImage, type RefKind } from '@/mocks/entities'

// Một nhóm ảnh mẫu (khuôn mặt hoặc ảnh hay bị dùng lại) của một đối tượng: tải lên, xem lớn, xoá.
export default function RefImageGroup({
  entity,
  refs,
  kind,
  title,
  description,
}: {
  entity: Entity
  refs: RefImage[]
  kind: RefKind
  title: string
  description: string
}) {
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [viewing, setViewing] = useState<RefImage | null>(null)
  const [deleting, setDeleting] = useState<RefImage | null>(null)

  const images = refs.filter((r) => r.entityId === entity.id && r.kind === kind)
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['refImages'] })

  const upload = useMutation({
    mutationFn: (files: File[]) => addRefImages(entity.id, kind, files),
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: (ref: RefImage) => deleteRefImage(ref.id),
    onSuccess: async () => {
      await refresh()
      setDeleting(null)
      setViewing(null)
    },
  })

  return (
    <section className="space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-medium">
            {title} <span className="text-sm font-normal text-muted-foreground">({images.length})</span>
          </h3>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        <input
          ref={fileInput}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(e) => {
            const files = Array.from(e.target.files ?? [])
            if (files.length > 0) upload.mutate(files)
            e.target.value = '' // cho phép chọn lại cùng file
          }}
        />
        <Button variant="outline" size="sm" onClick={() => fileInput.current?.click()} disabled={upload.isPending}>
          <UploadIcon />
          {upload.isPending ? 'Uploading…' : 'Upload'}
        </Button>
      </div>

      {upload.isError && <p className="text-sm text-destructive">Could not upload the images.</p>}

      {images.length === 0 ? (
        <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          No {title.toLowerCase()} yet.
        </p>
      ) : (
        <ul className="grid grid-cols-[repeat(auto-fill,minmax(8rem,1fr))] gap-3">
          {images.map((img) => (
            <li key={img.id} className="group relative">
              <button
                type="button"
                className="block w-full overflow-hidden rounded-lg border focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                onClick={() => setViewing(img)}
                aria-label={`View ${img.filename}`}
              >
                <RefThumb image={img} entityName={entity.name} className="w-full" />
              </button>
              <Button
                variant="secondary"
                size="icon-xs"
                className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                aria-label={`Delete ${img.filename}`}
                onClick={() => setDeleting(img)}
              >
                <Trash2Icon />
              </Button>
              <p className="mt-1 truncate text-xs text-muted-foreground" title={img.filename}>
                {img.filename}
              </p>
            </li>
          ))}
        </ul>
      )}

      {/* Xem ảnh lớn */}
      <Dialog open={viewing !== null} onOpenChange={(open) => !open && setViewing(null)}>
        <DialogContent className="sm:max-w-2xl">
          {viewing && (
            <>
              <DialogHeader>
                <DialogTitle>{viewing.filename}</DialogTitle>
                <DialogDescription>
                  {entity.name} · {title} · uploaded {formatVnDateTime(viewing.uploadedAt)}
                </DialogDescription>
              </DialogHeader>
              <RefThumb image={viewing} entityName={entity.name} large className="w-full max-h-[60vh] rounded-lg" />
              <DialogFooter>
                <Button variant="destructive" onClick={() => setDeleting(viewing)}>
                  <Trash2Icon />
                  Delete
                </Button>
                <DialogClose asChild>
                  <Button variant="outline">Close</Button>
                </DialogClose>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Xác nhận trước khi xoá */}
      <Dialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <DialogContent>
          {deleting && (
            <>
              <DialogHeader>
                <DialogTitle>Delete reference image?</DialogTitle>
                <DialogDescription>
                  {deleting.filename} will be removed from {entity.name}. Later analysis runs will no longer match
                  against it.
                </DialogDescription>
              </DialogHeader>
              {remove.isError && <p className="text-sm text-destructive">Could not delete the image.</p>}
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="outline">Cancel</Button>
                </DialogClose>
                <Button variant="destructive" onClick={() => remove.mutate(deleting)} disabled={remove.isPending}>
                  {remove.isPending ? 'Deleting…' : 'Delete'}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </section>
  )
}
