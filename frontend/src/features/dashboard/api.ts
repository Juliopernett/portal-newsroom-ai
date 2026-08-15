import { api } from '@/api/client'
import type { DashboardAlertas, RankingComercialItem } from '@/features/alertas/api'

export interface DashboardResumen {
  clientes_activos: number
  pautas_activas: number
  pautas_vencidas: number
  solicitudes_pendientes: number
  publicaciones_este_mes: number
  ingreso_contratado_activo: string
  ingreso_historico: string
  peso_comercial_promedio: string
  valor_promedio_por_cliente: string
}

export interface RentabilidadMensual {
  anio: number
  mes: number
  ingresos: string
  gastos: string
  rentabilidad: string
}

export const dashboardApi = {
  resumen: () => api.get<DashboardResumen>('/dashboard/resumen'),
  alertas: () => api.get<DashboardAlertas>('/dashboard/alertas'),
  ranking: () => api.get<RankingComercialItem[]>('/dashboard/ranking'),
  // desde/hasta default to the last 12 calendar months on the backend.
  rentabilidad: () => api.get<RentabilidadMensual[]>('/dashboard/rentabilidad'),
}
