import { api } from '@/api/client'

export interface User {
  id: string
  email: string
  nombre: string
}

export interface LoginPayload {
  email: string
  password: string
}

export const authApi = {
  login: (payload: LoginPayload) => api.post<User>('/auth/login', payload),
  logout: () => api.post<void>('/auth/logout'),
  me: () => api.get<User>('/auth/me'),
}
