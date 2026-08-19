import { api } from '@/api/client'

export type PautaTipo = 'individual' | 'mensual' | 'bimestral' | 'trimestral' | 'semestral' | 'anual'

export const PAUTA_TIPO_LABELS: Record<PautaTipo, string> = {
  individual: 'Individual',
  mensual: 'Mensual',
  bimestral: 'Bimestral',
  trimestral: 'Trimestral',
  semestral: 'Semestral',
  anual: 'Anual',
}

export interface Pauta {
  id: string
  client_id: string
  fecha_inicio: string
  fecha_fin: string
  publicaciones_contratadas: number
  valor_pagado: string
  fecha_pago: string
  saldo_pendiente: string
  fecha_registro: string
  observaciones: string | null
  publicaciones_consumidas: number
  publicaciones_restantes: number
  vigente: boolean
  vencida: boolean
  cuota_agotada: boolean
  peso_comercial: string
  tipo: PautaTipo
}

export interface PautaInput {
  client_id: string
  fecha_inicio: string
  fecha_fin: string
  publicaciones_contratadas: number
  valor_pagado: string
  fecha_pago: string
  saldo_pendiente: string
  observaciones: string | null
}

export const pautasApi = {
  list: () => api.get<Pauta[]>('/pautas'),
  create: (payload: PautaInput) => api.post<Pauta>('/pautas', payload),
  update: (id: string, payload: PautaInput) => api.put<Pauta>(`/pautas/${id}`, payload),
}
