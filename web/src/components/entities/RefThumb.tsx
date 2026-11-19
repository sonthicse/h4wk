import { cn } from '@/lib/utils'
import type { RefImage } from '@/api/entities'

// Ảnh mẫu lấy thẳng từ API (url của RefImage); cookie phiên đi kèm nên <img> tải được.
export default function RefThumb({ image, large = false, className }: { image: RefImage; large?: boolean; className?: string }) {
  return (
    <img
      src={image.url}
      alt={image.file}
      className={cn('aspect-square bg-muted', large ? 'object-contain' : 'object-cover', className)}
    />
  )
}
