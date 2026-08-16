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

export interface PlanCatalogo {
  id: string
  label: string
  cantidad: number
  valor: number
  dias: number
}

// El catálogo real de precios de Portal Vallenato — mismo id/valor que
// app/api/static/app.js (PLANES_CATALOGO). Es solo un atajo de captura
// (autocompleta cantidad/valor/fecha_fin en el formulario); no es un
// campo que se guarde en la Pauta.
export const PLANES_CATALOGO: PlanCatalogo[] = [
  { id: 'ind-1', label: '1 publicación — $100.000', cantidad: 1, valor: 100000, dias: 1 },
  { id: 'ind-2', label: '2 publicaciones — $150.000', cantidad: 2, valor: 150000, dias: 1 },
  { id: 'ind-3', label: '3 publicaciones — $190.000', cantidad: 3, valor: 190000, dias: 1 },
  { id: 'mes-1', label: '1 mes — $430.000', cantidad: 10, valor: 430000, dias: 30 },
  { id: 'mes-2', label: '2 meses — $760.000', cantidad: 20, valor: 760000, dias: 60 },
  { id: 'mes-3', label: '3 meses — $1.100.000', cantidad: 30, valor: 1100000, dias: 90 },
  { id: 'mes-6', label: '6 meses — $1.780.000', cantidad: 60, valor: 1780000, dias: 180 },
  { id: 'mes-12', label: '1 año — $3.050.000', cantidad: 120, valor: 3050000, dias: 365 },
]
