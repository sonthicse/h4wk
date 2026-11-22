import { cn } from '@/lib/utils'
import type { RefImage } from '@/api/entities'

export default function RefThumb({ image, large = false, className }: { image: RefImage; large?: boolean; className?: string }) {
  return (
    <img
      src={image.url}
      alt={image.file}
      className={cn('aspect-square bg-muted', large ? 'object-contain' : 'object-cover', className)}
    />
  )
}
