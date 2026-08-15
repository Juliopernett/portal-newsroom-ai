import { api } from '@/api/client'

export interface Gasto {
  id: string
  descripcion: string
  valor: string
  fecha: string
  fecha_registro: string
}

export interface GastoInput {
  descripcion: string
  valor: string
  fecha: string
}

export const gastosApi = {
  list: () => api.get<Gasto[]>('/gastos'),
  create: (payload: GastoInput) => api.post<Gasto>('/gastos', payload),
  update: (id: string, payload: GastoInput) => api.put<Gasto>(`/gastos/${id}`, payload),
  delete: (id: string) => api.delete<void>(`/gastos/${id}`),
}
