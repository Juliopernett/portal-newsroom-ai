import { api } from '@/api/client'

export type SolicitudEstado = 'recibida' | 'aceptada' | 'cancelada'

// Preparación editorial con IA (2026-08-21): PENDIENTE hasta el primer
// "Crear borrador" en WordPress, PROCESADO si la IA reescribió el texto,
// FALLIDO si no estuvo disponible — el borrador se crea igual con el
// texto original, ver DestinosPanel.
export type EstadoPreparacionIA = 'pendiente' | 'procesado' | 'fallido'

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
  contenido_editorial: string | null
  entradilla_editorial: string | null
  titulo_editorial: string | null
  categoria_editorial: string | null
  etiquetas_editorial: string[] | null
  slug_editorial: string | null
  meta_titulo_editorial: string | null
  meta_descripcion_editorial: string | null
  frase_clave_editorial: string | null
  preparacion_ia_estado: EstadoPreparacionIA
  preparacion_ia_error: string | null
}

export interface SolicitudCreateInput {
  pauta_id: string | null
  client_id: string | null
  titulo: string | null
  texto: string
  prioridad_manual: boolean
  canales: CanalPublicacion[]
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
  meta_post_id: string | null
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
  coincidencia: number | null
  ya_relacionada: boolean
}

export interface SolicitudContexto {
  titulo: string | null
  texto: string
  clienteNombre: string | null
  fechaRecepcion: string
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
  // Publicadas de un contrato vigente sin Facebook/Instagram todavía —
  // una sola consulta al backend (core.analytics.AnalyticsService
  // .solicitudes_sin_destino_social) en vez de un GET .../destinos por
  // solicitud candidata, que llegó a mandar ~180 peticiones simultáneas
  // y saturó la conexión un momento (2026-08-20).
  sinDestinoSocial: () => api.get<Solicitud[]>('/publication-requests/sin-destino-social'),
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
  // La preparación editorial con IA (2026-08-21) corre dentro de este mismo
  // llamado — la respuesta trae el destino más si la IA sí pudo prepararlo,
  // para que el toast en DestinosPanel sea honesto sin un fetch aparte.
  crearBorradorWordpress: (id: string, destinoId: string) =>
    api.post<{
      destino: DestinoPublicacion
      preparacion_ia_estado: EstadoPreparacionIA
      preparacion_ia_error: string | null
    }>(`/publication-requests/${id}/destinos/${destinoId}/crear-borrador-wordpress`),
  // Sincronización con el estado real de WordPress (2026-08-24): lectura
  // pura contra la API REST de WordPress vía wp_post_id, nunca una orden
  // de publicar. Se usa tanto en silencio (auto-sync al abrir la
  // solicitud) como detrás del botón "Confirmar publicado" de la fila de
  // WordPress, que dejó de marcar publicado a ciegas.
  sincronizarWordpress: (id: string, destinoId: string) =>
    api.post<DestinoPublicacion>(
      `/publication-requests/${id}/destinos/${destinoId}/sincronizar-wordpress`,
    ),
  confirmarDestino: (
    id: string,
    destinoId: string,
    urlPublicacion: string | null,
    metaPostId?: string | null,
  ) =>
    api.post<DestinoPublicacion>(
      `/publication-requests/${id}/destinos/${destinoId}/confirmar-publicacion`,
      {
        ...(urlPublicacion ? { url_publicacion: urlPublicacion } : {}),
        ...(metaPostId ? { meta_post_id: metaPostId } : {}),
      },
    ),
  cancelarDestino: (id: string, destinoId: string) =>
    api.post<DestinoPublicacion>(`/publication-requests/${id}/destinos/${destinoId}/cancelar`),
  corregirEnlaceDestino: (
    id: string,
    destinoId: string,
    canal: CanalPublicacion,
    enlace: string,
    metaPostId?: string | null,
  ) =>
    api.patch<DestinoPublicacion>(
      `/publication-requests/${id}/destinos/${destinoId}/corregir-enlace`,
      {
        ...(canal === 'wordpress' ? { wp_url: enlace } : { url_publicacion: enlace }),
        ...(metaPostId ? { meta_post_id: metaPostId } : {}),
      },
    ),
  // Contexto opcional (2026-08-20, conciliación inteligente): cuando se
  // pasa, el backend calcula coincidencia por post y ordena por ella —
  // ver GET /social/posts-recientes. Sin contexto, se comporta como
  // antes (solo recientes, sin puntaje).
  postsRecientes: (canal: Exclude<CanalPublicacion, 'wordpress'>, contexto?: SolicitudContexto) => {
    const params = new URLSearchParams({ canal })
    if (contexto) {
      if (contexto.titulo) params.set('solicitud_titulo', contexto.titulo)
      params.set('solicitud_texto', contexto.texto)
      if (contexto.clienteNombre) params.set('solicitud_cliente_nombre', contexto.clienteNombre)
      params.set('solicitud_fecha_recepcion', contexto.fechaRecepcion)
    }
    return api.get<PostRedSocial[]>(`/social/posts-recientes?${params.toString()}`)
  },

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
