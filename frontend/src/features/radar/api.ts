import { api } from '@/api/client'

export type EstadoNewsCandidate = 'nuevo' | 'guardado' | 'descartado' | 'procesado'

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
  // genera ninguna noticia todavía (Extractor/Writer llegan en un sprint
  // futuro). Ver el docstring de `core.services.news_candidate_service.crear_noticia`.
  crearNoticia: (id: string) => api.post<NewsCandidate>(`/discovery/${id}/crear-noticia`),
}
