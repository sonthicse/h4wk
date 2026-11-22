// Theme sáng/tối. Lựa chọn lưu ở localStorage; chưa chọn thì theo hệ điều hành.
// index.html có đoạn script cùng logic để áp theme trước khi React chạy (không nháy trắng).
export type Theme = 'light' | 'dark'

const KEY = 'h4wk-theme'

export function currentTheme(): Theme {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

export function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  // Favicon đảo màu theo theme: nét đen trên nền sáng, nét trắng trên nền tối.
  document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.setAttribute('href', theme === 'dark' ? '/logo-dark.svg' : '/favicon.svg')
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    // Trình duyệt chặn localStorage: theme vẫn đổi, chỉ không nhớ cho lần sau.
  }
}
