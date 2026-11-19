import { useQuery } from '@tanstack/react-query'
import {
  BriefcaseIcon,
  FolderIcon,
  DownloadIcon,
  EyeIcon,
  FlagIcon,
  LayoutDashboardIcon,
  ListChecksIcon,
  SettingsIcon,
  UsersIcon,
} from 'lucide-react'
import { useEffect } from 'react'
import { NavLink, useMatch, useParams } from 'react-router'
import { getCase, listCases } from '@/api/cases'
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

const caseNav = [
  { path: 'dashboard', label: 'Dashboard', icon: LayoutDashboardIcon },
  { path: 'collect', label: 'Collect', icon: DownloadIcon },
  { path: 'findings', label: 'Findings', icon: FlagIcon },
  { path: 'review', label: 'Review queue', icon: ListChecksIcon },
  { path: 'watchlist', label: 'Watchlist', icon: EyeIcon },
  { path: 'entities', label: 'Entities', icon: UsersIcon },
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

const LAST_CASE_KEY = 'h4wk.lastCase'

// localStorage có thể bị chặn (chế độ riêng tư); khi đó chỉ mất tính năng nhớ case.
function readLastCase(): string | null {
  try {
    return localStorage.getItem(LAST_CASE_KEY)
  } catch {
    return null
  }
}

function writeLastCase(id: string) {
  try {
    localStorage.setItem(LAST_CASE_KEY, id)
  } catch {
    // bỏ qua
  }
}

export default function AppSidebar() {
  const { caseId: routeCaseId } = useParams()
  const cases = useQuery({ queryKey: ['cases'], queryFn: listCases }).data ?? []

  // Ở trang không thuộc case nào (All cases, Settings) vẫn hiện menu của case mở gần nhất,
  // để sidebar giống nhau trên mọi trang. Case gần nhất nhớ trong trình duyệt.
  useEffect(() => {
    if (routeCaseId) writeLastCase(routeCaseId)
  }, [routeCaseId])
  const last = readLastCase()
  const caseId = routeCaseId ?? (last && cases.some((c) => c.id === last) ? last : cases[0]?.id)

  // Cùng queryKey với các trang dùng getCase nên chỉ gọi API một lần.
  const current = useQuery({ queryKey: ['case', caseId], queryFn: () => getCase(caseId!), enabled: !!caseId }).data

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
              <NavItem to="/cases" label="All cases" icon={BriefcaseIcon} />
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        {/* Danh sách case để chuyển nhanh, có ở mọi trang (kể cả Cases và Settings); ẩn khi thu gọn. */}
        {cases.length > 0 && (
          <SidebarGroup className="group-data-[collapsible=icon]:hidden">
            <SidebarGroupLabel>Cases</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {cases.map((c) => (
                  <SidebarMenuItem key={c.id}>
                    <SidebarMenuButton asChild isActive={c.id === routeCaseId}>
                      <NavLink to={`/cases/${c.id}/collect`}>
                        <FolderIcon />
                        <span>{c.title}</span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
        {caseId && (
          <SidebarGroup>
            {/* Giữ chỗ cho nhãn khi thu gọn (mặc định shadcn kéo -mt-8) để icon bên dưới không nhảy lên. */}
            <SidebarGroupLabel className="group-data-[collapsible=icon]:mt-0">{current?.title ?? caseId}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {caseNav.map((item) => (
                  <NavItem key={item.path} to={`/cases/${caseId}/${item.path}`} label={item.label} icon={item.icon} />
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
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
