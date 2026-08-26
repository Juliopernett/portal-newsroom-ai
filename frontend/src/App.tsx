import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'

import { AuthProvider } from '@/features/auth/AuthProvider'
import { LoginPage } from '@/features/auth/LoginPage'
import { ProtectedRoute } from '@/features/auth/ProtectedRoute'
import { Shell } from '@/app/Shell'
import { useFaviconIdentidad } from '@/app/AppLogo'
import { GastosPage } from '@/features/gastos/GastosPage'
import { ClientesPage } from '@/features/clientes/ClientesPage'
import { ReportesPage } from '@/features/reportes/ReportesPage'
import { ContratosPage } from '@/features/contratos/ContratosPage'
import { SolicitudesPage } from '@/features/solicitudes/SolicitudesPage'
import { RadarPage } from '@/features/radar/RadarPage'
import { AlertasPage } from '@/features/alertas/AlertasPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { ConfiguracionPage } from '@/features/configuracion/ConfiguracionPage'

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
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<Shell />}>
                <Route index element={<DashboardPage />} />
                <Route path="alertas" element={<AlertasPage />} />
                <Route path="solicitudes" element={<SolicitudesPage />} />
                <Route path="radar" element={<RadarPage />} />
                <Route path="clientes" element={<ClientesPage />} />
                <Route path="contratos" element={<ContratosPage />} />
                <Route path="gastos" element={<GastosPage />} />
                <Route path="reportes" element={<ReportesPage />} />
                <Route path="configuracion" element={<ConfiguracionPage />} />
              </Route>
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
