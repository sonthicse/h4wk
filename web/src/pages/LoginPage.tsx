import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { login } from '@/api/auth'
import { UnauthorizedError } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import Logo from '@/components/Logo'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  // Trang người dùng định vào trước khi bị chuyển sang đây (RequireLogin gửi kèm).
  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  const signIn = useMutation({
    mutationFn: () => login(username.trim(), password),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['me'] })
      navigate(from, { replace: true })
    },
  })

  let error = ''
  if (signIn.error instanceof UnauthorizedError) error = 'Wrong username or password.'
  else if (signIn.error) error = 'Could not reach the server. Try again.'

  return (
    <div className="flex min-h-svh items-center justify-center bg-muted px-4">
      <Card className="w-full max-w-md min-h-140 justify-center py-12">
        <CardHeader className="flex flex-col items-center gap-4 px-10">
          <Logo className="size-28 rounded-[28px] text-[56px]" />
          <CardTitle className="text-2xl">
            <h1>Sign in</h1>
          </CardTitle>
        </CardHeader>
        <CardContent className="px-10">
          <form
            className="space-y-5"
            onSubmit={(e) => {
              e.preventDefault()
              if (username.trim() && password) signIn.mutate()
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                autoComplete="username"
                className="h-10"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                className="h-10"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <Button
              type="submit"
              className="h-10 w-full"
              disabled={!username.trim() || !password || signIn.isPending}
            >
              {signIn.isPending ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
