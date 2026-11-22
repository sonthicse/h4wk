import { MoonIcon, SunIcon } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { applyTheme, currentTheme } from '@/lib/theme'

// Nút đổi giữa giao diện sáng và tối.
export default function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = useState(currentTheme)
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      className={className}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
      onClick={() => {
        applyTheme(next)
        setTheme(next)
      }}
    >
      {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
    </Button>
  )
}
