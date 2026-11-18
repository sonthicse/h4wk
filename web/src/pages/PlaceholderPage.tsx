// Trang giữ chỗ cho các màn chưa làm; mỗi màn có task riêng trong tasks/todo.md.
export default function PlaceholderPage({ title, task }: { title: string; task: string }) {
  return (
    <div className="space-y-2">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-muted-foreground">Not built yet ({task}).</p>
    </div>
  )
}
