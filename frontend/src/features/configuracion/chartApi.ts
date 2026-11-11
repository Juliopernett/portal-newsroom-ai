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
  regenerarEdicion: (semana: string) => api.post<Edicion>(`${BASE}/ediciones/${semana}/regenerar`),
  publicarEdicion: (semana: string) => api.post<Edicion>(`${BASE}/ediciones/${semana}/publicar`),
  decidir: (
    videoId: string,
    cambio: { excluido?: boolean; fijar_en?: number; quitar_fijo?: boolean },
  ) => api.patch<VideoSeguido>(`${BASE}/videos/${videoId}`, cambio),
}
