import { ApiError } from '@/api/client'

export type VariantePortada = 'noticias' | 'lo_ultimo'

// Qué parte de la foto queda en la portada: enfoques de 0 a 1 y zoom desde 1.
export interface Encuadre {
  enfoqueX: number
  enfoqueY: number
  zoom: number
}

export const ENCUADRE_INICIAL: Encuadre = { enfoqueX: 0.5, enfoqueY: 0.3, zoom: 1 }

export interface GenerarPortadaInput extends Encuadre {
  imagenBase: File
  imagenCirculo: File | null
  titular: string
  antetitulo: string
  variante: VariantePortada
}

export const portadasApi = {
  // `api.postForm` parsea JSON; este endpoint devuelve la imagen ya
  // renderizada, así que se lee como Blob (la cookie de sesión va igual).
  async generar(input: GenerarPortadaInput): Promise<Blob> {
    const form = new FormData()
    form.append('imagen_base', input.imagenBase)
    if (input.imagenCirculo) form.append('imagen_circulo', input.imagenCirculo)
    form.append('titular', input.titular)
    if (input.antetitulo.trim()) form.append('antetitulo', input.antetitulo.trim())
    form.append('variante', input.variante)
    form.append('enfoque_x', String(input.enfoqueX))
    form.append('enfoque_y', String(input.enfoqueY))
    form.append('zoom', String(input.zoom))
    const res = await fetch('/portadas', { method: 'POST', body: form, credentials: 'include' })
    if (!res.ok) {
      const body = await res.json().catch(() => null)
      throw new ApiError(res.status, body?.detail ?? `Error ${res.status}`)
    }
    return res.blob()
  },
}
