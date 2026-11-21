// Mọi thời gian trên giao diện hiện theo giờ Việt Nam (SPEC 6).
const TZ = 'Asia/Ho_Chi_Minh'

// Dạng `HH:MM dd/mm/yyyy`, giờ Việt Nam, ví dụ `13:20 20/11/2026`.
export function formatVnDateTime(iso: string) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', {
      timeZone: TZ,
      hour12: false,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
      .formatToParts(new Date(iso))
      .map((x) => [x.type, x.value]),
  )
  const hour = p.hour === '24' ? '00' : p.hour
  return `${hour}:${p.minute} ${p.day}/${p.month}/${p.year}`
}

export function formatVnTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-GB', { timeZone: TZ })
}
