import { api } from '@/api/client'

export type SolicitudEstado = 'recibida' | 'aceptada' | 'cancelada'

export interface Solicitud {
  id: string
  pauta_id: string | null
  fecha_recepcion: string
  titulo: string | null
  texto: string
  estado: SolicitudEstado
  prioridad_manual: boolean
  observaciones: string | null
  fecha_cierre: string | null
}

export interface SolicitudCreateInput {
  pauta_id: string | null
  titulo: string | null
  texto: string
  prioridad_manual: boolean
}

export interface SolicitudEditInput {
  titulo?: string
  texto?: string
  prioridad_manual?: boolean
}

export interface SolicitudesKanban {
  pendientes: Solicitud[]
  publicadas: Solicitud[]
}

export const solicitudesApi = {
  // Three parallel requests, same split the legacy app uses: "recibida"
  // comes back from the backend already in work order (prioridad manual >
  // peso comercial > fecha de recepción — AnalyticsService), "aceptada"
  // but not yet completa still belongs in the work queue (not a state
  // this V1's UI manages further, but it must not disappear from the
  // board), and "completa" (fecha_cierre set) is the Publicadas column.
  async loadKanban(): Promise<SolicitudesKanban> {
    const [recibidas, enCurso, publicadas] = await Promise.all([
      api.get<Solicitud[]>('/publication-requests?estado=recibida'),
      api.get<Solicitud[]>('/publication-requests?estado=aceptada&completa=false'),
      api.get<Solicitud[]>('/publication-requests?completa=true'),
    ])
    publicadas.sort((a, b) => (b.fecha_cierre ?? '').localeCompare(a.fecha_cierre ?? ''))
    return { pendientes: [...recibidas, ...enCurso], publicadas }
  },
  create: (payload: SolicitudCreateInput) => api.post<Solicitud>('/publication-requests', payload),
  edit: (id: string, payload: SolicitudEditInput) =>
    api.patch<Solicitud>(`/publication-requests/${id}`, payload),
  publish: (id: string) => api.post<Solicitud>(`/publication-requests/${id}/publish`),
  cancelar: (id: string) => api.post<Solicitud>(`/publication-requests/${id}/cancelar`),
  linkPauta: (id: string, pautaId: string) =>
    api.post<Solicitud>(`/publication-requests/${id}/link-pauta`, { pauta_id: pautaId }),
}
