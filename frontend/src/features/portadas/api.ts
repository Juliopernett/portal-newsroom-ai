import { ApiError } from '@/api/client'

export type VariantePortada = 'noticias' | 'lo_ultimo'

export interface GenerarPortadaInput {
  imagenBase: File
  imagenCirculo: File | null
  titular: string
  antetitulo: string
  variante: VariantePortada
  enfoqueX: number
  enfoqueY: number
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
    const res = await fetch('/portadas', { method: 'POST', body: form, credentials: 'include' })
    if (!res.ok) {
      const body = await res.json().catch(() => null)
      throw new ApiError(res.status, body?.detail ?? `Error ${res.status}`)
    }
    return res.blob()
  },
}
