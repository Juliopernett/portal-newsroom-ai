import { Suspense, lazy } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'

import { AuthProvider } from '@/features/auth/AuthProvider'
import { LoginPage } from '@/features/auth/LoginPage'
import { ProtectedRoute } from '@/features/auth/ProtectedRoute'
import { Shell } from '@/app/Shell'
import { useFaviconIdentidad } from '@/app/AppLogo'

// Each page is its own chunk: a phone on mobile data only downloads the
// screen it opens (recharts etc. no longer ship with the login page).
const GastosPage = lazy(() => import('@/features/gastos/GastosPage').then((m) => ({ default: m.GastosPage })))
const ClientesPage = lazy(() => import('@/features/clientes/ClientesPage').then((m) => ({ default: m.ClientesPage })))
const ReportesPage = lazy(() => import('@/features/reportes/ReportesPage').then((m) => ({ default: m.ReportesPage })))
const ContratosPage = lazy(() => import('@/features/contratos/ContratosPage').then((m) => ({ default: m.ContratosPage })))
const SolicitudesPage = lazy(() => import('@/features/solicitudes/SolicitudesPage').then((m) => ({ default: m.SolicitudesPage })))
const PortadasPage = lazy(() => import('@/features/portadas/PortadasPage').then((m) => ({ default: m.PortadasPage })))
const RadarPage = lazy(() => import('@/features/radar/RadarPage').then((m) => ({ default: m.RadarPage })))
const AlertasPage = lazy(() => import('@/features/alertas/AlertasPage').then((m) => ({ default: m.AlertasPage })))
const DashboardPage = lazy(() => import('@/features/dashboard/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const ConfiguracionPage = lazy(() => import('@/features/configuracion/ConfiguracionPage').then((m) => ({ default: m.ConfiguracionPage })))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
})

export default function App() {
  useFaviconIdentidad()

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Toaster
            position="top-right"
            richColors
            toastOptions={{
              classNames: {
                toast: 'font-sans',
              },
            }}
          />
          <Suspense fallback={<p className="p-6 text-sm text-muted-foreground">Cargando…</p>}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<Shell />}>
                <Route index element={<DashboardPage />} />
                <Route path="alertas" element={<AlertasPage />} />
                <Route path="solicitudes" element={<SolicitudesPage />} />
                <Route path="radar" element={<RadarPage />} />
                <Route path="portadas" element={<PortadasPage />} />
                <Route path="clientes" element={<ClientesPage />} />
                <Route path="contratos" element={<ContratosPage />} />
                <Route path="gastos" element={<GastosPage />} />
                <Route path="reportes" element={<ReportesPage />} />
                <Route path="configuracion" element={<ConfiguracionPage />} />
              </Route>
            </Route>
          </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
