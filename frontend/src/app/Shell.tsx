import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Inbox,
  ClipboardList,
  Users,
  FileText,
  Wallet,
  Download,
  LogOut,
} from 'lucide-react'

import { cn } from '@/lib/utils'
import { useAuth } from '@/features/auth/AuthProvider'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/alertas', label: 'Alertas', icon: Inbox, end: false },
  { to: '/solicitudes', label: 'Solicitudes', icon: ClipboardList, end: false },
  { to: '/clientes', label: 'Clientes', icon: Users, end: false },
  { to: '/contratos', label: 'Contratos', icon: FileText, end: false },
  { to: '/gastos', label: 'Gastos', icon: Wallet, end: false },
  { to: '/reportes', label: 'Reportes', icon: Download, end: false },
] as const

export function Shell() {
  const { user, logout } = useAuth()

  return (
    <div className="flex min-h-svh">
      <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-card">
        <div className="px-4 py-5">
          <p className="text-sm font-semibold">Portal Newsroom AI</p>
          {user && <p className="truncate text-xs text-muted-foreground">{user.nombre}</p>}
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-2">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand text-brand-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                )
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-2 pb-4">
          <button
            type="button"
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <LogOut className="size-4" />
            Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
