import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { LogOutIcon } from 'lucide-react'
import { useNavigate } from 'react-router'
import { getMe, logout } from '@/api/auth'
import ThemeToggle from '@/components/ThemeToggle'
import { Button } from '@/components/ui/button'

export default function UserMenu() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const me = useQuery({ queryKey: ['me'], queryFn: getMe, retry: false })

  const signOut = useMutation({
    mutationFn: logout,
    onSettled: () => {
      queryClient.clear()
      navigate('/login', { replace: true })
    },
  })

  return (
    <div className="ml-auto flex items-center gap-2">
      <span className="font-mono text-sm text-muted-foreground">{me.data ? `user:${me.data.username}` : ''}</span>
      <ThemeToggle />
      <Button variant="ghost" size="sm" onClick={() => signOut.mutate()} disabled={signOut.isPending}>
        <LogOutIcon />
        Sign out
      </Button>
    </div>
  )
}
