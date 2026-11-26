import { api, ApiError } from '@/api/client'

export interface ColoresMarca {
  fondo: string
  destacado: string
  texto_destacado: string
}

// Los de portalvallenato.com (los mismos valores por defecto del backend).
export const COLORES_WEB: ColoresMarca = {
  fondo: '#3B5998',
  destacado: '#E1CE26',
  texto_destacado: '#083A7A',
}

export type Pieza = 'portada' | 'radar'

export const coloresApi = {
  get: () => api.get<ColoresMarca>('/colores-marca'),
  save: (colores: ColoresMarca) => api.put<ColoresMarca>('/colores-marca', colores),
  // Devuelve la imagen ya dibujada, así que se lee como Blob.
  async vistaPrevia(pieza: Pieza, colores: ColoresMarca): Promise<Blob> {
    const query = new URLSearchParams({ pieza, ...colores })
    const res = await fetch(`/colores-marca/vista-previa?${query}`, { credentials: 'include' })
    if (!res.ok) throw new ApiError(res.status, `Error ${res.status}`)
    return res.blob()
  },
}
