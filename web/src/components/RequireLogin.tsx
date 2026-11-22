import { useQuery } from '@tanstack/react-query'
import { Navigate, Outlet, useLocation } from 'react-router'
import { getMe } from '@/api/auth'
import { UnauthorizedError } from '@/api/client'

export default function RequireLogin() {
  const location = useLocation()
  const me = useQuery({ queryKey: ['me'], queryFn: getMe, retry: false })

  if (me.isPending) return <p className="p-6 text-sm text-muted-foreground">Loading…</p>
  if (me.error instanceof UnauthorizedError) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  if (me.error) {
    return <p className="p-6 text-sm text-destructive">Could not reach the API. Is the backend running?</p>
  }
  return <Outlet />
}
