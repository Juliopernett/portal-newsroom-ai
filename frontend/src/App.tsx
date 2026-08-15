import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { AuthProvider } from '@/features/auth/AuthProvider'
import { LoginPage } from '@/features/auth/LoginPage'
import { ProtectedRoute } from '@/features/auth/ProtectedRoute'
import { Shell } from '@/app/Shell'
import { PlaceholderPage } from '@/app/PlaceholderPage'
import { GastosPage } from '@/features/gastos/GastosPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<Shell />}>
                <Route index element={<PlaceholderPage title="Dashboard" />} />
                <Route path="alertas" element={<PlaceholderPage title="Alertas" />} />
                <Route path="solicitudes" element={<PlaceholderPage title="Solicitudes" />} />
                <Route path="clientes" element={<PlaceholderPage title="Clientes" />} />
                <Route path="contratos" element={<PlaceholderPage title="Contratos" />} />
                <Route path="gastos" element={<GastosPage />} />
              </Route>
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
