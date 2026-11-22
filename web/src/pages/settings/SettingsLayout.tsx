import { NavLink, Outlet } from 'react-router'
import { cn } from '@/lib/utils'

// Khung trang Settings (SPEC 10.10): mục 1–5 ở Sources, phần Jev ở tab Jev, luồng và chu kỳ watchlist ở tab Watchlist.
const tabs = [
  { to: '/settings/sources', label: 'Sources' },
  { to: '/settings/jev', label: 'Jev' },
  { to: '/settings/watchlist', label: 'Watchlist' },
]

export default function SettingsLayout() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <nav className="flex gap-1 border-b" aria-label="Settings sections">
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            className={({ isActive }) =>
              cn(
                '-mb-px border-b-2 px-3 py-2 text-sm',
                isActive ? 'border-primary font-medium' : 'border-transparent text-muted-foreground hover:text-foreground',
              )
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
