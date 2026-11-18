// Mọi thời gian trên giao diện hiện theo giờ Việt Nam (SPEC 6).
const TZ = 'Asia/Ho_Chi_Minh'

export function formatVnDateTime(iso: string) {
  return new Date(iso).toLocaleString('en-GB', { timeZone: TZ })
}

export function formatVnTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-GB', { timeZone: TZ })
}
