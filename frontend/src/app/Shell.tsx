import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutDashboard,
  Inbox,
  ClipboardList,
  Users,
  FileText,
  Wallet,
  Download,
  LogOut,
  Menu,
  Settings,
  X,
} from 'lucide-react'

import { cn } from '@/lib/utils'
import { useAuth } from '@/features/auth/AuthProvider'
import { insightsApi } from '@/features/alertas/api'
import { centroAlertaKey, useDismissedAlerts } from '@/features/alertas/utils'
import logoMark from '@/assets/logo-mark.png'

// Grouped by utility rather than one flat list: Dashboard/Alertas stay
// ungrouped (analítica, se consultan solas), "Comercial" agrupa las tres
// vistas que giran alrededor del mismo cliente (cliente → contrato →
// solicitud), y "Finanzas" separa lo contable. Un label de grupo, no un
// acordeón — no cuesta clics extra, solo hace explícito el parentesco.
const NAV_GROUPS = [
  {
    label: null,
    items: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
      { to: '/alertas', label: 'Alertas', icon: Inbox, end: false },
    ],
  },
  {
    label: 'Comercial',
    items: [
      { to: '/clientes', label: 'Clientes', icon: Users, end: false },
      { to: '/contratos', label: 'Contratos', icon: FileText, end: false },
      { to: '/solicitudes', label: 'Solicitudes', icon: ClipboardList, end: false },
    ],
  },
  {
    label: 'Finanzas',
    items: [
      { to: '/gastos', label: 'Ingresos y gastos', icon: Wallet, end: false },
      { to: '/reportes', label: 'Reportes', icon: Download, end: false },
    ],
  },
  {
    label: 'Sistema',
    items: [{ to: '/configuracion', label: 'Configuración', icon: Settings, end: false }],
  },
] as const

export function Shell() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)

  // Same query key AlertasPage uses, so whichever loads first primes the
  // other's cache — this is just a lightweight badge, not a poller. Grouped
  // and dismiss-filtered the same way AlertasPage renders Centro de
  // Alertas, so the badge count never disagrees with what the page shows.
  const centroQuery = useQuery({ queryKey: ['insights', 'centro-alertas'], queryFn: insightsApi.centroAlertas })
  const { isDismissed } = useDismissedAlerts()
  const alertasCount = new Set(
    (centroQuery.data ?? [])
      .filter((item) => !isDismissed(centroAlertaKey(item)))
      .map((item) => centroAlertaKey(item)),
  ).size

  // Close the mobile drawer on every navigation — it doesn't unmount on
  // its own since Shell stays mounted across route changes.
  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  return (
    <div className="flex h-svh flex-col md:flex-row">
      <header className="flex shrink-0 items-center justify-between border-b border-border bg-card px-4 py-3 md:hidden">
        <div className="flex items-center gap-2">
          <img src={logoMark} alt="" className="size-6" />
          <p className="text-sm font-semibold">Portal Vallenato Newsroom</p>
        </div>
        <button
          type="button"
          aria-label={mobileOpen ? 'Cerrar menú' : 'Abrir menú'}
          onClick={() => setMobileOpen((v) => !v)}
          className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        >
          {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </header>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 flex-col border-r border-border bg-card transition-transform duration-200',
          'md:static md:z-auto md:w-56 md:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="hidden items-center gap-2 px-4 py-5 md:flex">
          <img src={logoMark} alt="" className="size-8 shrink-0" />
          <div>
            <p className="text-sm font-semibold">Portal Vallenato Newsroom</p>
            {user && <p className="truncate text-xs text-muted-foreground">{user.nombre}</p>}
          </div>
        </div>
        <div className="flex items-center justify-between px-4 py-4 md:hidden">
          <div className="flex items-center gap-2">
            <img src={logoMark} alt="" className="size-7 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Portal Vallenato Newsroom</p>
              {user && <p className="truncate text-xs text-muted-foreground">{user.nombre}</p>}
            </div>
          </div>
          <button
            type="button"
            aria-label="Cerrar menú"
            onClick={() => setMobileOpen(false)}
            className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          >
            <X className="size-5" />
          </button>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-2">
          {NAV_GROUPS.map((group) => (
            <div key={group.label ?? 'root'} className="flex flex-col gap-1">
              {group.label && (
                <p className="px-3 pt-3 pb-1 text-[.68rem] font-semibold tracking-wide text-muted-foreground uppercase">
                  {group.label}
                </p>
              )}
              {group.items.map(({ to, label, icon: Icon, end }) => (
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
                  {to === '/alertas' && alertasCount > 0 && (
                    <span className="ml-auto flex size-5 shrink-0 items-center justify-center rounded-full bg-danger text-xs font-semibold text-white">
                      {alertasCount > 9 ? '9+' : alertasCount}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
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
      <main className="flex-1 overflow-y-auto p-4 md:p-6">
        <Outlet />
      </main>
    </div>
  )
}
