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
import { NavLink, useMatch } from 'react-router'
import { getHealth } from '@/api/health'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
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

function NavItem({ to, label, icon: Icon, end = true }: { to: string; label: string; icon: typeof FlagIcon; end?: boolean }) {
  return (
    <SidebarMenuItem>
      <SidebarMenuButton asChild isActive={useMatch({ path: to, end }) !== null} tooltip={label}>
        <NavLink to={to} end={end}>
          <Icon />
          <span>{label}</span>
        </NavLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  )
}

function ApiStatus() {
  const { data, error, isPending } = useQuery({ queryKey: ['health'], queryFn: getHealth })

  let status = 'loading…'
  if (error) status = 'unreachable'
  else if (!isPending) status = data.status

  return (
    <p className="px-2 text-xs text-muted-foreground group-data-[collapsible=icon]:hidden">
      API: <span data-testid="api-status" className="font-mono text-foreground">{status}</span>
    </p>
  )
}

export default function AppSidebar() {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        {/* Chỗ đặt logo: kích thước cố định để menu không nhảy khi thu gọn sidebar. */}
        <div className="flex items-center gap-2">
          <div
            aria-label="Logo"
            className="size-8 shrink-0 rounded-md border border-dashed border-muted-foreground/40"
          />
          {/* Ẩn chữ khi thu gọn; ô logo giữ nguyên kích thước nên menu không nhảy. */}
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
          <NavItem to="/settings" label="Settings" icon={SettingsIcon} end={false} />
        </SidebarMenu>
        <ApiStatus />
      </SidebarFooter>
    </Sidebar>
  )
}
