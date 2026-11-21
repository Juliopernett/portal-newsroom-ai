import { api } from '@/api/client'
import type { Client } from '@/features/clientes/api'
import type { PautaTipo } from '@/features/contratos/api'

export interface SaldoPauta {
  pauta_id: string
  tipo: PautaTipo
  saldo_pendiente: string
  fecha_pago: string
  fecha_fin: string
  dias_desde_pago: number
  vencida: boolean
}

export interface Deudor {
  cliente: Client
  total_pendiente: string
  dias_mas_antiguo: number
  saldos: SaldoPauta[]
}

export interface Deudores {
  total_por_cobrar: string
  cantidad: number
  deudores: Deudor[]
}

export const deudoresApi = {
  list: () => api.get<Deudores>('/deudores'),
}
