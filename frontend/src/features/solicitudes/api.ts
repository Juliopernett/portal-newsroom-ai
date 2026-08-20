import { api } from '@/api/client'

export type SolicitudEstado = 'recibida' | 'aceptada' | 'cancelada'

export interface Solicitud {
  id: string
  pauta_id: string | null
  client_id: string | null
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
  client_id: string | null
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

export type CanalPublicacion = 'wordpress' | 'facebook' | 'instagram'
export type EstadoDestino = 'pendiente' | 'publicado' | 'fallido' | 'cancelado'

export interface DestinoPublicacion {
  id: string
  publication_request_id: string
  canal: CanalPublicacion
  estado: EstadoDestino
  wp_post_id: string | null
  wp_url: string | null
  url_publicacion: string | null
  registrado_por_user_id: string | null
  fecha_publicacion: string | null
  ultimo_error: string | null
}

export type MediaAssetTipo = 'imagen' | 'video'

export interface MediaAsset {
  id: string
  publication_request_id: string
  tipo: MediaAssetTipo
  nombre_archivo: string
  content_type: string
  tamano_bytes: number
  fecha_subida: string
  subido_por_user_id: string | null
}

export interface PostRedSocial {
  id: string
  canal: CanalPublicacion
  permalink: string
  texto: string
  miniatura_url: string | null
  fecha_publicacion: string
}

export interface ReporteDestino {
  canal: CanalPublicacion
  estado: EstadoDestino
  enlace: string | null
  fecha_publicacion: string | null
  ultimo_error: string | null
}

export interface ReporteSolicitud {
  publication_request_id: string
  titulo: string | null
  texto: string
  cliente_nombre: string | null
  pauta_id: string | null
  fecha_recepcion: string
  fecha_cierre: string | null
  completa: boolean
  pauta_consumida: boolean
  destinos: ReporteDestino[]
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

  // Destinos (multi-canal — WordPress/Facebook/Instagram)
  listDestinos: (id: string) => api.get<DestinoPublicacion[]>(`/publication-requests/${id}/destinos`),
  addDestino: (id: string, canal: CanalPublicacion) =>
    api.post<DestinoPublicacion>(`/publication-requests/${id}/destinos`, { canal }),
  crearBorradorWordpress: (id: string, destinoId: string) =>
    api.post<DestinoPublicacion>(
      `/publication-requests/${id}/destinos/${destinoId}/crear-borrador-wordpress`,
    ),
  confirmarDestino: (id: string, destinoId: string, urlPublicacion: string | null) =>
    api.post<DestinoPublicacion>(
      `/publication-requests/${id}/destinos/${destinoId}/confirmar-publicacion`,
      urlPublicacion ? { url_publicacion: urlPublicacion } : {},
    ),
  cancelarDestino: (id: string, destinoId: string) =>
    api.post<DestinoPublicacion>(`/publication-requests/${id}/destinos/${destinoId}/cancelar`),
  corregirEnlaceDestino: (id: string, destinoId: string, canal: CanalPublicacion, enlace: string) =>
    api.patch<DestinoPublicacion>(
      `/publication-requests/${id}/destinos/${destinoId}/corregir-enlace`,
      canal === 'wordpress' ? { wp_url: enlace } : { url_publicacion: enlace },
    ),
  postsRecientes: (canal: Exclude<CanalPublicacion, 'wordpress'>) =>
    api.get<PostRedSocial[]>(`/social/posts-recientes?canal=${canal}`),

  // Reporte (read-only, generated on demand, never persisted)
  getReporte: (id: string) => api.get<ReporteSolicitud>(`/publication-requests/${id}/reporte`),

  // Media (imágenes/videos adjuntos)
  listMedia: (id: string) => api.get<MediaAsset[]>(`/publication-requests/${id}/media`),
  uploadMedia: (id: string, file: File) => {
    const form = new FormData()
    form.append('archivo', file)
    return api.postForm<MediaAsset>(`/publication-requests/${id}/media`, form)
  },
  deleteMedia: (id: string, mediaId: string) =>
    api.delete<void>(`/publication-requests/${id}/media/${mediaId}`),
  mediaContentUrl: (id: string, mediaId: string) =>
    `/publication-requests/${id}/media/${mediaId}/contenido`,
}
