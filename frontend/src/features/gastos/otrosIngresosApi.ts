import { api } from '@/api/client'

export interface OtroIngreso {
  id: string
  origen: string
  monto: string
  monto_usd: string | null
  fecha_cobro: string
  observaciones: string | null
  fecha_registro: string
}

export interface OtroIngresoInput {
  origen: string
  monto: string
  monto_usd: string | null
  fecha_cobro: string
  observaciones: string | null
}

export const otrosIngresosApi = {
  list: () => api.get<OtroIngreso[]>('/otros-ingresos'),
  create: (payload: OtroIngresoInput) => api.post<OtroIngreso>('/otros-ingresos', payload),
  update: (id: string, payload: OtroIngresoInput) =>
    api.put<OtroIngreso>(`/otros-ingresos/${id}`, payload),
  delete: (id: string) => api.delete<void>(`/otros-ingresos/${id}`),
}
