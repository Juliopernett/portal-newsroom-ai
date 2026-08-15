import { api } from '@/api/client'

export type ClientType = 'artista' | 'manager' | 'promotor' | 'empresario'

export const CLIENT_TYPE_LABELS: Record<ClientType, string> = {
  artista: 'Artista',
  manager: 'Manager',
  promotor: 'Promotor',
  empresario: 'Empresario',
}

export interface Client {
  id: string
  nombre: string
  tipo: ClientType
  telefono: string
  instagram: string | null
  observaciones: string | null
}

export interface ClientInput {
  nombre: string
  tipo: ClientType
  telefono: string
  instagram: string | null
  observaciones: string | null
}

export const clientsApi = {
  list: () => api.get<Client[]>('/clients'),
  create: (payload: ClientInput) => api.post<Client>('/clients', payload),
  update: (id: string, payload: ClientInput) => api.put<Client>(`/clients/${id}`, payload),
}
