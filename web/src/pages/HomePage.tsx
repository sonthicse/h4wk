import { useQuery } from '@tanstack/react-query'
import { getHealth } from '@/api/health'

export default function HomePage() {
  const { data, error, isPending } = useQuery({ queryKey: ['health'], queryFn: getHealth })

  let status = 'loading…'
  if (error) status = 'unreachable'
  else if (!isPending) status = data.status

  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="text-2xl font-semibold">h4wk</h1>
      <p className="mt-4 text-muted-foreground">
        API status: <span data-testid="api-status" className="font-mono text-foreground">{status}</span>
      </p>
    </main>
  )
}
