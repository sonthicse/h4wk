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
      <Card className="w-full max-w-md py-10">
        <CardHeader className="flex flex-col items-center gap-4 px-10">
          {/* Chỗ đặt logo, sẽ thay bằng ảnh logo khi có. */}
          <div aria-label="Logo" className="size-64 rounded-3xl border border-dashed border-muted-foreground/40" />
          <CardTitle className="text-xl">Sign in</CardTitle>
        </CardHeader>
        <CardContent className="px-10">
          <form
            className="space-y-5"
            onSubmit={(e) => {
              e.preventDefault()
              navigate('/cases')
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input id="username" autoComplete="username" className="h-10" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" autoComplete="current-password" className="h-10" />
            </div>
            <Button type="submit" className="h-10 w-full">Sign in</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
