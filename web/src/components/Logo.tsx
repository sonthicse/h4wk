import { cn } from '@/lib/utils'

// Logo theo bản phác: ô vuông bo góc nền đậm, chữ "h". Cỡ, bo góc và cỡ chữ do nơi dùng truyền qua className.
export default function Logo({ className }: { className?: string }) {
  return (
    <span
      role="img"
      aria-label="h4wk logo"
      className={cn('flex items-center justify-center bg-primary font-semibold text-primary-foreground', className)}
    >
      h
    </span>
  )
}
