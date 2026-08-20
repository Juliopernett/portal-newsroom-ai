import { api } from '@/api/client'
import type { Client } from '@/features/clientes/api'
import type { PautaTipo } from '@/features/contratos/api'
import type { Solicitud } from '@/features/solicitudes/api'

export type NivelSalud = 'excelente' | 'bueno' | 'regular' | 'riesgo' | 'critico'
export type AlertaSeveridad = 'critica' | 'atencion' | 'informativa'
export type AccionSugerida =
  | 'renovar'
  | 'contactar'
  | 'cobrar'
  | 'reactivar'
  | 'ver_cliente'
  | 'ver_solicitudes'
  | 'ninguna'
export type PatronComercialTipo =
  | 'consumo_alto'
  | 'nunca_premium'
  | 'recurrencia_mensual'
  | 'racha_renovaciones'
  | 'tipo_habitual'

export interface ClienteScoreSalud {
  cliente: Client
  score: number
  estrellas: number
  nivel: NivelSalud
}

export interface AlertaInteligente {
  tipo: string
  severidad: AlertaSeveridad
  mensaje: string
  cliente: Client | null
  accion: AccionSugerida
  dias: number | null
}

export interface ClienteRiesgoAbandono {
  cliente: Client
  dias_sin_actividad: number
  publicaciones_restantes: number
  fecha_vencimiento: string
}

export interface ClienteDormido {
  cliente: Client
  dias_sin_actividad: number
  ultimo_contrato_tipo: PautaTipo
  ultimo_contrato_fecha_fin: string
}

export interface ClienteCuentaPorCobrar {
  cliente: Client
  pauta_id: string
  saldo_pendiente: string
  tipo: PautaTipo
  fecha_fin: string
}

export interface OportunidadComercial {
  cliente: Client
  tipo: PatronComercialTipo
  mensaje: string
  racha: number | null
  tipo_habitual: PautaTipo | null
  porcentaje_consumido: string | null
}

export const insightsApi = {
  centroAlertas: () => api.get<AlertaInteligente[]>('/insights/centro-alertas'),
  riesgoAbandono: () => api.get<ClienteRiesgoAbandono[]>('/insights/riesgo-abandono'),
  cuentasPorCobrar: () => api.get<ClienteCuentaPorCobrar[]>('/insights/cuentas-por-cobrar'),
  dormidos: () => api.get<ClienteDormido[]>('/insights/dormidos'),
  saludClientes: () => api.get<ClienteScoreSalud[]>('/insights/salud-clientes'),
  oportunidades: () => api.get<OportunidadComercial[]>('/insights/oportunidades'),
}

export interface DashboardAlertas {
  clientes_cupo_agotado: Client[]
  clientes_por_vencer: Client[]
  clientes_menos_de_3_restantes: Client[]
  clientes_individuales_pendientes: Client[]
  clientes_contrato_por_renovar: Client[]
  solicitudes_antiguas: Solicitud[]
  clientes_publicaciones_sin_usar: Client[]
  clientes_premium: Client[]
}

export interface RankingComercialItem {
  cliente: Client
  valor_contratado: string
  peso_comercial: string
  tipo: PautaTipo
  publicaciones_contratadas: number
  publicaciones_restantes: number
  fecha_vencimiento: string
  vigente: boolean
  estado_comercial: string
  pauta_id: string
}

export const dashboardApi = {
  alertas: () => api.get<DashboardAlertas>('/dashboard/alertas'),
  ranking: () => api.get<RankingComercialItem[]>('/dashboard/ranking'),
}
