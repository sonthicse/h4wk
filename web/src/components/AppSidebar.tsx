import { useQuery } from '@tanstack/react-query'
import {
  BriefcaseIcon,
  DownloadIcon,
  EyeIcon,
  FlagIcon,
  LayoutDashboardIcon,
  ListChecksIcon,
  SettingsIcon,
  UsersIcon,
} from 'lucide-react'
import { NavLink, useMatch, useParams } from 'react-router'
import { getHealth } from '@/api/health'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { cases } from '@/mocks/data'

const caseNav = [
  { path: 'dashboard', label: 'Dashboard', icon: LayoutDashboardIcon },
  { path: 'collect', label: 'Collect', icon: DownloadIcon },
  { path: 'findings', label: 'Findings', icon: FlagIcon },
  { path: 'review', label: 'Review queue', icon: ListChecksIcon },
  { path: 'watchlist', label: 'Watchlist', icon: EyeIcon },
  { path: 'entities', label: 'Entities', icon: UsersIcon },
]

function NavItem({ to, label, icon: Icon }: { to: string; label: string; icon: typeof FlagIcon }) {
  return (
    <SidebarMenuItem>
      <SidebarMenuButton asChild isActive={useMatch({ path: to, end: true }) !== null} tooltip={label}>
        <NavLink to={to} end>
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
  const { caseId } = useParams()
  const current = cases.find((c) => c.id === caseId)

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        {/* Chỗ đặt logo: kích thước cố định để menu không nhảy khi thu gọn sidebar. */}
        <div
          aria-label="Logo"
          className="size-8 shrink-0 rounded-md border border-dashed border-muted-foreground/40"
        />
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <NavItem to="/cases" label="Cases" icon={BriefcaseIcon} />
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        {current && (
          <SidebarGroup>
            {/* Giữ chỗ cho nhãn khi thu gọn (mặc định shadcn kéo -mt-8) để icon bên dưới không nhảy lên. */}
            <SidebarGroupLabel className="group-data-[collapsible=icon]:mt-0">{current.name}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {caseNav.map((item) => (
                  <NavItem key={item.path} to={`/cases/${current.id}/${item.path}`} label={item.label} icon={item.icon} />
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <NavItem to="/settings" label="Settings" icon={SettingsIcon} />
        </SidebarMenu>
        <ApiStatus />
      </SidebarFooter>
    </Sidebar>
  )
}
