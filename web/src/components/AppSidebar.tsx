import { Highlight, HighlightItem } from '@animate-ui/react/primitives/effects/highlight'
import { useQuery } from '@tanstack/react-query'
import {
  DownloadIcon,
  EyeIcon,
  FlagIcon,
  LayoutDashboardIcon,
  ListChecksIcon,
  SettingsIcon,
  UsersIcon,
  VideoIcon,
} from 'lucide-react'
import { NavLink, useLocation } from 'react-router'
import { getHealth } from '@/api/health'
import Logo from '@/components/Logo'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
} from '@/components/ui/sidebar'

const nav = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboardIcon },
  { path: '/collect', label: 'Collect', icon: DownloadIcon },
  { path: '/videos', label: 'Videos', icon: VideoIcon },
  { path: '/findings', label: 'Findings', icon: FlagIcon },
  { path: '/review', label: 'Review queue', icon: ListChecksIcon },
  { path: '/watchlist', label: 'Watchlist', icon: EyeIcon },
  { path: '/entities', label: 'Entities', icon: UsersIcon },
]

const settingsNav = { path: '/settings', label: 'Settings', icon: SettingsIcon }

function useActivePath() {
  const { pathname } = useLocation()
  return [...nav, settingsNav].find((i) => pathname === i.path || pathname.startsWith(`${i.path}/`))?.path ?? null
}

function NavItem({ to, label, icon: Icon }: { to: string; label: string; icon: typeof FlagIcon }) {
  return (
    <HighlightItem as="li" value={to} className="group/menu-item" data-slot="sidebar-menu-item" data-sidebar="menu-item">
      <SidebarMenuButton
        asChild
        data-slot="sidebar-menu-button"
        isActive={useActivePath() === to}
        tooltip={label}
        className="hover:bg-sidebar-accent/50 data-active:bg-transparent"
      >
        <NavLink to={to}>
          <Icon />
          <span>{label}</span>
        </NavLink>
      </SidebarMenuButton>
    </HighlightItem>
  )
}

function ApiStatus() {

  const { error, isPending } = useQuery({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 15000 })

  let label = 'Connecting to API…'
  let dot = 'bg-muted-foreground'
  if (error) {
    label = 'API unreachable'
    dot = 'bg-destructive'
  } else if (!isPending) {
    label = 'API connected'
    dot = 'bg-green-600'
  }

  return (
    <p className="flex items-center gap-1.5 p-2 text-xs text-muted-foreground group-data-[collapsible=icon]:hidden">
      <span aria-hidden="true" className={`size-2 shrink-0 rounded-full ${dot}`} />
      <span data-testid="api-status">{label}</span>
    </p>
  )
}

export default function AppSidebar() {
  const active = useActivePath()
  return (
    <Sidebar collapsible="icon">
      <Highlight controlledItems value={active} hover={false} click={false} className="inset-0 rounded-md bg-sidebar-accent">
        <SidebarHeader>
          <div className="flex items-center gap-2">
            <Logo className="size-8 shrink-0" />
            <span className="text-lg font-semibold group-data-[collapsible=icon]:hidden">h4wk</span>
          </div>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                {nav.map((item) => (
                  <NavItem key={item.path} to={item.path} label={item.label} icon={item.icon} />
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <SidebarMenu>
            <NavItem to={settingsNav.path} label={settingsNav.label} icon={settingsNav.icon} />
          </SidebarMenu>
          <ApiStatus />
        </SidebarFooter>
      </Highlight>
    </Sidebar>
  )
}
