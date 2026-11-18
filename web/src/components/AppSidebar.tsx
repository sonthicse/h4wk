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
        <span className="px-2 text-lg font-semibold group-data-[collapsible=icon]:hidden">h4wk</span>
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
            <SidebarGroupLabel>{current.name}</SidebarGroupLabel>
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
