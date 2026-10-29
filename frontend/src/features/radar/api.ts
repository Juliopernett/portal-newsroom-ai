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
  // Sprint Discovery 5 — borrador creado en WordPress por "Crear noticia".
  wp_post_id: string | null
  wp_url: string | null
  // Sprint Portadas — portada generada, ya subida a WordPress.
  portada_url: string | null
}

// Opciones de portada de "Crear noticia" — todas opcionales: sin
// `imagenBase` el borrador se crea sin imagen destacada.
export interface OpcionesPortada {
  imagenBase: File
  imagenCirculo: File | null
  variante: 'noticias' | 'lo_ultimo'
  titular: string
  antetitulo: string
}

export const radarApi = {
  // Los candidatos nunca se crean desde la API — solo
  // `python -m scripts.descubrir_noticias` los persiste. "Actualizar
  // Radar" (2026-08-26) solo vuelve a leer lo ya guardado, nunca dispara
  // el descubrimiento en sí.
  listar: () => api.get<NewsCandidate[]>('/discovery'),
  guardar: (id: string) => api.post<NewsCandidate>(`/discovery/${id}/guardar`),
  descartar: (id: string) => api.post<NewsCandidate>(`/discovery/${id}/descartar`),
  // Sprint Discovery 5: redacta con IA y crea el BORRADOR en WordPress
  // (nunca publica) y marca el candidato "procesado". Requiere haber
  // pulsado "Preparar noticia" antes.
  crearNoticia: (id: string, portada?: OpcionesPortada | null) => {
    if (!portada) return api.post<NewsCandidate>(`/discovery/${id}/crear-noticia`)
    const form = new FormData()
    form.append('imagen_base', portada.imagenBase)
    if (portada.imagenCirculo) form.append('imagen_circulo', portada.imagenCirculo)
    form.append('variante', portada.variante)
    if (portada.titular.trim()) form.append('titular_portada', portada.titular.trim())
    if (portada.antetitulo.trim()) form.append('antetitulo', portada.antetitulo.trim())
    return api.postForm<NewsCandidate>(`/discovery/${id}/crear-noticia`, form)
  },
  // Sprint Discovery 3: resuelve la fuente real y extrae su contenido —
  // acción técnica, repetible, independiente de "Crear noticia".
  preparar: (id: string) => api.post<NewsCandidate>(`/discovery/${id}/preparar`),
}
