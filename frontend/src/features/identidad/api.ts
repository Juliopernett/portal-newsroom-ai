import { api, ApiError } from '@/api/client'

export interface IdentidadComercial {
  id: string
  nombre_comercial: string
  razon_social: string | null
  nit: string | null
  telefono: string | null
  email: string | null
  sitio_web: string | null
  instagram: string | null
  facebook: string | null
  otras_redes: string | null
  logo_storage_key: string | null
  fecha_actualizacion: string
  tiene_logo: boolean
}

export interface IdentidadComercialInput {
  nombre_comercial: string
  razon_social: string | null
  nit: string | null
  telefono: string | null
  email: string | null
  sitio_web: string | null
  instagram: string | null
  facebook: string | null
  otras_redes: string | null
}

export const LOGO_URL = '/identidad-comercial/logo'

export const identidadApi = {
  get: async () => {
    try {
      return await api.get<IdentidadComercial>('/identidad-comercial')
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null
      throw err
    }
  },
  save: (payload: IdentidadComercialInput) => api.put<IdentidadComercial>('/identidad-comercial', payload),
  uploadLogo: (file: File) => {
    const form = new FormData()
    form.append('archivo', file)
    return api.postForm<IdentidadComercial>('/identidad-comercial/logo', form)
  },
}
