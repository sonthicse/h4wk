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

// Trang con (ví dụ /videos/:id, /videos/:id/captures/:capture) vẫn chọn mục cha, xem useActivePath.
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

// Mục đang chọn: khớp đúng path hoặc path con; không khớp mục nào (vd /login) thì không có chỉ báo.
function useActivePath() {
  const { pathname } = useLocation()
  return [...nav, settingsNav].find((i) => pathname === i.path || pathname.startsWith(`${i.path}/`))?.path ?? null
}

// Nền chỉ báo do Highlight vẽ và trượt giữa các mục, nên nền active tĩnh của nút được tắt; hover giữ nền nhạt cho mục chưa chọn.
// data-slot truyền lại vì thư viện ghi đè data-slot của vỏ và của nút bằng giá trị của nó.
// HighlightItem thay cho SidebarMenuItem: vỏ <li> có đúng một con là nút (thư viện clone con để đặt z-index).
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
  const active = useActivePath()
  return (
    <Sidebar collapsible="icon">
      {/* Một Highlight bọc cả menu chính và Settings ở footer để chỉ báo trượt qua cả hai. */}
      <Highlight controlledItems value={active} hover={false} click={false} className="inset-0 rounded-md bg-sidebar-accent">
        <SidebarHeader>
          {/* Ô logo giữ kích thước cố định để menu không nhảy khi thu gọn sidebar. */}
          <div className="flex items-center gap-2">
            <Logo className="size-8 shrink-0" />
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
            <NavItem to={settingsNav.path} label={settingsNav.label} icon={settingsNav.icon} />
          </SidebarMenu>
          <ApiStatus />
        </SidebarFooter>
      </Highlight>
    </Sidebar>
  )
}
