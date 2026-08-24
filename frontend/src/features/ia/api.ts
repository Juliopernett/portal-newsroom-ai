import { api } from '@/api/client'

export type ProveedorIA = 'anthropic' | 'openrouter'

export interface AIConfiguracion {
  id: string
  proveedor: ProveedorIA
  modelo: string
}

export interface AIConfiguracionInput {
  proveedor: ProveedorIA
  modelo: string
}

export const aiConfiguracionApi = {
  get: () => api.get<AIConfiguracion>('/ai-configuracion'),
  save: (payload: AIConfiguracionInput) => api.put<AIConfiguracion>('/ai-configuracion', payload),
}
