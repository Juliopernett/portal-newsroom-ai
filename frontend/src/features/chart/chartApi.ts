import { api } from '@/api/client'

export interface FilaChart {
  posicion: number
  video_id: string
  titulo: string
  artista: string | null
  miniatura_url: string | null
  url: string
  vistas_semana: number
  vistas_totales: number
  tendencia: 'sube' | 'baja' | 'igual' | 'nuevo' | null
  posicion_anterior: number | null
  fijado: boolean
  parcial: boolean
}

export interface VideoSeguido {
  video_id: string
  titulo: string
  artista: string | null
  url: string
  manual: boolean
  excluido: boolean
  es_short: boolean
  duracion_segundos: number | null
  fijado_posicion: number | null
  vistas_semana: number | null
}

export interface ChartAdmin {
  actualizado: string | null
  youtube_configurado: boolean
  filas: FilaChart[]
  videos: VideoSeguido[]
}

export interface CanalChart {
  canal_id: string
  nombre: string
  artista: string | null
  activo: boolean
}

export interface Recoleccion {
  canales_ok: number
  canales_con_error: string[]
  videos_nuevos: number
  videos_seguidos: number
  snapshots: number
  error_estadisticas: string | null
}

export interface FilaEdicion {
  posicion: number
  video_id: string
  titulo: string
  artista: string | null
  miniatura_url: string | null
  url: string
  vistas_semana: number
  vistas_totales: number
  tendencia: 'sube' | 'baja' | 'igual' | 'nuevo' | null
  posicion_anterior: number | null
  fijado: boolean
}

export interface EdicionResumen {
  semana_fin: string
  estado: 'borrador' | 'publicada'
  filas: number
  sin_base: number
  generada_en: string | null
  publicada_en: string | null
}

export interface Edicion extends EdicionResumen {
  filas_detalle: FilaEdicion[]
}

export interface EstadoSemanal {
  semana_fin: string
  nivel: 'ok' | 'info' | 'atencion' | 'error'
  mensaje: string
}

const BASE = '/chart-vallenato'

export type LaminaChart = 'portada' | 'lista'
export type FormatoChart = 'feed' | 'historia'

export const chartApi = {
  obtener: () => api.get<ChartAdmin>(BASE),
  recolectar: () => api.post<Recoleccion>(`${BASE}/recolectar`),
  canales: () => api.get<CanalChart[]>(`${BASE}/canales`),
  agregarCanal: (referencia: string, artista: string | null) =>
    api.post<CanalChart>(`${BASE}/canales`, { referencia, artista }),
  quitarCanal: (canalId: string) => api.delete<void>(`${BASE}/canales/${canalId}`),
  agregarVideo: (referencia: string, artista: string | null) =>
    api.post<VideoSeguido>(`${BASE}/videos`, { referencia, artista }),
  estadoSemanal: () => api.get<EstadoSemanal>(`${BASE}/estado-semanal`),
  ediciones: () => api.get<EdicionResumen[]>(`${BASE}/ediciones`),
  edicion: (semana: string) => api.get<Edicion>(`${BASE}/ediciones/${semana}`),
  // Imagen PNG para redes (la sesión viaja por cookie, así que un enlace de descarga basta).
  urlImagen: (semana: string, lamina: LaminaChart, formato: FormatoChart) =>
    `${BASE}/ediciones/${semana}/imagen?lamina=${lamina}&formato=${formato}`,
  // Baja la imagen desde la app (con la cookie) y devuelve el Blob PNG. Un enlace directo
  // con `download` falla en el teléfono: el gestor de descargas no lleva la sesión y guarda
  // la página HTML de login en vez de la imagen.
  async descargarImagen(semana: string, lamina: LaminaChart, formato: FormatoChart): Promise<Blob> {
    const res = await fetch(`${BASE}/ediciones/${semana}/imagen?lamina=${lamina}&formato=${formato}`, {
      credentials: 'include',
    })
    const tipo = res.headers.get('content-type') ?? ''
    if (!res.ok || !tipo.startsWith('image/')) {
      throw new Error(res.ok ? 'La sesión venció: vuelve a entrar e inténtalo de nuevo' : `Error ${res.status}`)
    }
    return new Blob([await res.blob()], { type: 'image/png' })
  },
  // Vista previa del Top 10 en vivo (marca de agua, solo se ve; nunca se descarga).
  urlImagenEnVivo: (lamina: LaminaChart, formato: FormatoChart, version = 0) =>
    `${BASE}/en-vivo/imagen?lamina=${lamina}&formato=${formato}&v=${version}`,
  textoRedes: (semana: string) => api.get<{ texto: string }>(`${BASE}/ediciones/${semana}/texto`),
  regenerarEdicion: (semana: string) => api.post<Edicion>(`${BASE}/ediciones/${semana}/regenerar`),
  publicarEdicion: (semana: string) => api.post<Edicion>(`${BASE}/ediciones/${semana}/publicar`),
  decidir: (
    videoId: string,
    cambio: { excluido?: boolean; fijar_en?: number; quitar_fijo?: boolean },
  ) => api.patch<VideoSeguido>(`${BASE}/videos/${videoId}`, cambio),
}
