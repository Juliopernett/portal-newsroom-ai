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
  incluye_metricas: boolean
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
  incluye_metricas: boolean
}

export interface InformeLink {
  url: string
  expira_en: string
}

export interface MetricasPost {
  alcance: number | null
  vistas: number | null
  reacciones: number | null
  comentarios: number | null
  compartidos: number | null
  guardados: number | null
  interacciones: number | null
}

export interface FilaMetrica {
  destino_id: string
  solicitud_id: string
  titulo: string
  canal: 'facebook' | 'instagram'
  url: string | null
  tiene_meta_post_id: boolean
  capturado_en: string | null
  metricas: MetricasPost | null
}

export interface MetricasPauta {
  incluye_metricas: boolean
  resumen: {
    publicaciones_total: number
    publicaciones_con_datos: number
    publicaciones_sin_datos: number
    alcance_total: number | null
    vistas_total: number | null
    interacciones_total: number | null
  }
  filas: FilaMetrica[]
  errores: string[]
}

export const pautasApi = {
  metricas: (id: string) => api.get<MetricasPauta>(`/pautas/${id}/metricas`),
  actualizarMetricas: (id: string) => api.post<MetricasPauta>(`/pautas/${id}/metricas/actualizar`),
  list: () => api.get<Pauta[]>('/pautas'),
  create: (payload: PautaInput) => api.post<Pauta>('/pautas', payload),
  update: (id: string, payload: PautaInput) => api.put<Pauta>(`/pautas/${id}`, payload),
  crearInformeLink: (id: string) => api.post<InformeLink>(`/pautas/${id}/informe-link`),
  crearContratoLink: (id: string) => api.post<InformeLink>(`/pautas/${id}/contrato-link`),
}
