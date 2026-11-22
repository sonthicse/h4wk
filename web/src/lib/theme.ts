

export type Theme = 'light' | 'dark'

const KEY = 'h4wk-theme'

export function currentTheme(): Theme {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

export function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')

  document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.setAttribute('href', theme === 'dark' ? '/logo-dark.svg' : '/favicon.svg')
  try {
    localStorage.setItem(KEY, theme)
  } catch {

  }
}
