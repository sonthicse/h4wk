import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

// Chưa có xác thực thật (T7); bấm Sign in chỉ chuyển sang trang Cases.
export default function LoginPage() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-svh items-center justify-center bg-muted">
      <Card className="w-80">
        <CardHeader>
          <CardTitle>Sign in to h4wk</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault()
              navigate('/cases')
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input id="username" autoComplete="username" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" autoComplete="current-password" />
            </div>
            <Button type="submit" className="w-full">Sign in</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
