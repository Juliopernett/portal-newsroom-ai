import { api } from '@/api/client'

export interface PlanPauta {
  id: string
  nombre: string
  cantidad_publicaciones: number
  valor: string
  dias_vigencia: number
  orden: number
  fecha_registro: string
}

export interface PlanPautaInput {
  nombre: string
  cantidad_publicaciones: number
  valor: string
  dias_vigencia: number
  orden: number
}

export const planesPautaApi = {
  list: () => api.get<PlanPauta[]>('/planes-pauta'),
  create: (payload: PlanPautaInput) => api.post<PlanPauta>('/planes-pauta', payload),
  update: (id: string, payload: PlanPautaInput) => api.put<PlanPauta>(`/planes-pauta/${id}`, payload),
  delete: (id: string) => api.delete<void>(`/planes-pauta/${id}`),
}
