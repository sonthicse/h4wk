import { ImageIcon, UserRoundIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RefImage } from '@/mocks/entities'

// Chữ cái đầu của từ đầu và từ cuối: "Nguyễn Văn A" → "NA".
function initials(name: string) {
  const words = name.trim().split(/\s+/).filter(Boolean)
  if (words.length === 0) return '?'
  const first = words[0][0]
  const last = words.length > 1 ? words[words.length - 1][0] : ''
  return (first + last).toUpperCase()
}

// Màu nền cố định theo id ảnh để mỗi ô placeholder dễ phân biệt.
function hue(id: string) {
  let h = 0
  for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) % 360
  return h
}

// Ảnh mẫu: có url (ảnh vừa tải lên) thì hiện ảnh; dữ liệu giả không có file thì vẽ ô placeholder.
export default function RefThumb({
  image,
  entityName,
  large = false,
  className,
}: {
  image: RefImage
  entityName: string
  large?: boolean
  className?: string
}) {
  if (image.url) {
    return <img src={image.url} alt={image.filename} className={cn('aspect-square', large ? 'bg-muted object-contain' : 'object-cover', className)} />
  }
  const Icon = image.kind === 'face' ? UserRoundIcon : ImageIcon
  return (
    <div
      role="img"
      aria-label={`${image.filename} (placeholder)`}
      className={cn('relative flex aspect-square items-center justify-center text-white', className)}
      style={{ background: `linear-gradient(135deg, hsl(${hue(image.id)} 45% 45%), hsl(${hue(image.id) + 40} 45% 30%))` }}
    >
      <span className={cn('font-semibold opacity-90', large ? 'text-8xl' : 'text-2xl')}>{initials(entityName)}</span>
      <Icon className={cn('absolute opacity-70', large ? 'right-4 bottom-4 size-8' : 'right-1.5 bottom-1.5 size-4')} />
    </div>
  )
}
