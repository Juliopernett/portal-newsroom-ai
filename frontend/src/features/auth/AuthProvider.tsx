import { createContext, use, useMemo, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError } from '@/api/client'
import { authApi, type LoginPayload, type User } from './api'

interface AuthContextValue {
  user: User | undefined
  isLoading: boolean
  login: (payload: LoginPayload) => Promise<User>
  loginError: string | null
  isLoggingIn: boolean
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const ME_KEY = ['auth', 'me']

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()

  const meQuery = useQuery({
    queryKey: ME_KEY,
    queryFn: authApi.me,
    // A 401 here just means "not logged in" — don't burn retries on it.
    retry: false,
  })

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: (user) => {
      queryClient.setQueryData(ME_KEY, user)
    },
  })

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      queryClient.setQueryData(ME_KEY, undefined)
      queryClient.clear()
    },
  })

  const value = useMemo<AuthContextValue>(
    () => ({
      user: meQuery.data,
      isLoading: meQuery.isLoading,
      login: (payload) => loginMutation.mutateAsync(payload),
      loginError:
        loginMutation.error instanceof ApiError ? loginMutation.error.message : null,
      isLoggingIn: loginMutation.isPending,
      logout: () => logoutMutation.mutate(),
    }),
    [meQuery.data, meQuery.isLoading, loginMutation, logoutMutation],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}

export function useAuth() {
  const ctx = use(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
