import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
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
import { deleteRef, listRefs, uploadRef, type Entity, type RefImage, type RefKind } from '@/api/entities'

// Một nhóm ảnh mẫu (khuôn mặt hoặc ảnh hay bị dùng lại) của một đối tượng: tải lên, xem lớn, xoá.
export default function RefImageGroup({
  entity,
  kind,
  title,
  description,
}: {
  entity: Entity
  kind: RefKind
  title: string
  description: string
}) {
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [viewing, setViewing] = useState<RefImage | null>(null)
  const [deleting, setDeleting] = useState<RefImage | null>(null)

  const refs = useQuery({ queryKey: ['refs', entity.id], queryFn: () => listRefs(entity.id) })
  const images = refs.data?.[kind] ?? []
  // Đổi ảnh thì số ảnh trong danh sách đối tượng cũng đổi.
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['refs', entity.id] }),
      queryClient.invalidateQueries({ queryKey: ['entities'] }),
    ])

  const upload = useMutation({
    mutationFn: async (files: File[]) => {
      for (const f of files) await uploadRef(entity.id, kind, f)
    },
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: (ref: RefImage) => deleteRef(ref),
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
          accept="image/jpeg,image/png,image/webp"
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

      {upload.error && <p className="text-sm text-destructive">Could not upload: {upload.error.message}</p>}
      {refs.error && <p className="text-sm text-destructive">Could not load images: {refs.error.message}</p>}

      {images.length === 0 ? (
        <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          No {title.toLowerCase()} yet.
        </p>
      ) : (
        <ul className="grid grid-cols-[repeat(auto-fill,minmax(8rem,1fr))] gap-3">
          {images.map((img) => (
            <li key={img.file} className="group relative">
              <button
                type="button"
                className="block w-full overflow-hidden rounded-lg border focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                onClick={() => setViewing(img)}
                aria-label={`View ${img.file}`}
              >
                <RefThumb image={img} className="w-full" />
              </button>
              <Button
                variant="secondary"
                size="icon-xs"
                className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                aria-label={`Delete ${img.file}`}
                onClick={() => setDeleting(img)}
              >
                <Trash2Icon />
              </Button>
              <p className="mt-1 truncate text-xs text-muted-foreground" title={img.file}>
                {img.file}
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
                <DialogTitle className="truncate">{viewing.file}</DialogTitle>
                <DialogDescription>
                  {entity.name} · {title} · uploaded {formatVnDateTime(viewing.uploaded_at)} · {(viewing.bytes / 1024).toFixed(0)} KB
                </DialogDescription>
              </DialogHeader>
              <RefThumb image={viewing} large className="w-full max-h-[60vh] rounded-lg" />
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
                  {deleting.file} will be removed from {entity.name}. Later analysis runs will no longer match
                  against it.
                </DialogDescription>
              </DialogHeader>
              {remove.error && <p className="text-sm text-destructive">Could not delete: {remove.error.message}</p>}
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
