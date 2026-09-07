import { api } from '@/api/client'

export type EstadoNewsCandidate = 'nuevo' | 'guardado' | 'descartado' | 'procesado'
// Sprint Discovery 3 — resolver la URL de Google Noticias a la fuente real.
export type EstadoResolucionFuente = 'pendiente' | 'resuelta' | 'fallida'

export interface ExtractedContent {
  title: string
  body: string
  source_url: string
  author: string | null
  published_at: string | null
  site_name: string | null
  image_urls: string[]
}

export interface NewsCandidate {
  id: string
  source: string
  title: string
  url: string
  summary: string
  image_url: string | null
  published_at: string | null
  discovered_at: string
  metadata: Record<string, string>
  confidence: number
  estado: EstadoNewsCandidate
  url_fuente_original: string | null
  estado_resolucion: EstadoResolucionFuente
  extracted_content: ExtractedContent | null
}

export const radarApi = {
  // Los candidatos nunca se crean desde la API — solo
  // `python -m scripts.descubrir_noticias` los persiste. "Actualizar
  // Radar" (2026-08-26) solo vuelve a leer lo ya guardado, nunca dispara
  // el descubrimiento en sí.
  listar: () => api.get<NewsCandidate[]>('/discovery'),
  guardar: (id: string) => api.post<NewsCandidate>(`/discovery/${id}/guardar`),
  descartar: (id: string) => api.post<NewsCandidate>(`/discovery/${id}/descartar`),
  // Sprint Discovery 2: solo transiciona el estado a "procesado" — no
  // genera ninguna noticia todavía (el agente Writer no existe aún).
  // Ver el docstring de `core.services.news_candidate_service.crear_noticia`.
  crearNoticia: (id: string) => api.post<NewsCandidate>(`/discovery/${id}/crear-noticia`),
  // Sprint Discovery 3: resuelve la fuente real y extrae su contenido —
  // acción técnica, repetible, independiente de "Crear noticia".
  preparar: (id: string) => api.post<NewsCandidate>(`/discovery/${id}/preparar`),
}
