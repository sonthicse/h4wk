import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { TriangleAlertIcon } from 'lucide-react'
import { useState } from 'react'
import { deleteJevKey, getJevSettings, setJevKey } from '@/api/settings'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

// Key Jev lưu riêng (không qua nút Save của trang): đặt hoặc xoá có hiệu lực ngay.
export default function JevCard() {
  const queryClient = useQueryClient()
  const jev = useQuery({ queryKey: ['jev-settings'], queryFn: getJevSettings })
  const [value, setValue] = useState('')
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['jev-settings'] })

  const save = useMutation({
    mutationFn: () => setJevKey(value.trim()),
    onSuccess: () => {
      setValue('')
      return refresh()
    },
  })
  const remove = useMutation({ mutationFn: deleteJevKey, onSuccess: refresh })
  const busy = save.isPending || remove.isPending
  const key = jev.data?.key
  const error = save.error ?? remove.error

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Jev (TypeSafe)
          {key && (
            <Badge variant={key.set ? 'default' : 'outline'}>
              {key.set ? `Key set${key.origin ? ` · ${key.origin}` : ''}` : 'No key'}
            </Badge>
          )}
        </CardTitle>
        <CardDescription>Classifies every speech segment and comment. Not a task route: it needs only an API key.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {jev.error && <p className="text-sm text-destructive">Could not load Jev settings.</p>}
        {key && !key.set && (
          <Alert>
            <TriangleAlertIcon />
            <AlertTitle>Jev is off</AlertTitle>
            <AlertDescription>Comments and speech use only the static layer.</AlertDescription>
          </Alert>
        )}
        {key?.set && <p className="font-mono text-sm text-muted-foreground">{key.masked}</p>}
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (value.trim()) save.mutate()
          }}
        >
          <Input
            type="password"
            autoComplete="off"
            aria-label="Jev API key"
            placeholder={key?.set ? 'Replace the key' : 'TypeSafe API key'}
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          <Button type="submit" disabled={busy || !value.trim()}>
            {save.isPending ? 'Saving…' : 'Save key'}
          </Button>
          {key?.set && key.origin === 'settings' && (
            <Button type="button" variant="outline" disabled={busy} onClick={() => remove.mutate()}>
              Remove
            </Button>
          )}
        </form>
        {error && <p role="alert" className="text-sm text-destructive">{error.message}</p>}
      </CardContent>
    </Card>
  )
}
