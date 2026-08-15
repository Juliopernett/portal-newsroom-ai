import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Phone, Plus, RefreshCw, Search } from 'lucide-react'
import { toast } from 'sonner'

import { ApiError } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { CLIENT_TYPE_LABELS, clientsApi, type Client, type ClientInput } from './api'
import { ClienteForm } from './ClienteForm'

const CLIENTS_KEY = ['clients']

export function ClientesPage() {
  const queryClient = useQueryClient()
  const location = useLocation()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [sheetOpen, setSheetOpen] = useState(false)
  const [editing, setEditing] = useState<Client | null>(null)

  // Cross-module deep link (from Alertas' "Ver cliente") — same
  // navigation-state pattern as Contratos' preselectClientId.
  useEffect(() => {
    const state = location.state as { buscar?: string } | null
    if (state?.buscar) {
      setSearch(state.buscar)
      navigate(location.pathname, { replace: true, state: null })
    }
  }, [location.state, location.pathname, navigate])

  const clientsQuery = useQuery({ queryKey: CLIENTS_KEY, queryFn: clientsApi.list })

  const createMutation = useMutation({
    mutationFn: clientsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CLIENTS_KEY })
      setSheetOpen(false)
      toast.success('Cliente creado.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (payload: ClientInput) => clientsApi.update(editing!.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CLIENTS_KEY })
      setSheetOpen(false)
      toast.success('Cliente actualizado.')
    },
  })

  const clientesFiltrados = useMemo(() => {
    const clientes = clientsQuery.data ?? []
    const termino = search.trim().toLowerCase()
    if (!termino) return clientes
    return clientes.filter((c) => c.nombre.toLowerCase().includes(termino))
  }, [clientsQuery.data, search])

  function openNew() {
    setEditing(null)
    createMutation.reset()
    updateMutation.reset()
    setSheetOpen(true)
  }

  function openEdit(client: Client) {
    setEditing(client)
    createMutation.reset()
    updateMutation.reset()
    setSheetOpen(true)
  }

  const activeMutation = editing ? updateMutation : createMutation
  const mutationError = activeMutation.error instanceof ApiError ? activeMutation.error.message : null

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">Clientes</h1>
          <p className="text-sm text-muted-foreground">Fichas comerciales de cada cliente</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={openNew}>
            <Plus /> Nuevo cliente
          </Button>
          <Button
            variant="outline"
            size="icon"
            aria-label="Actualizar"
            onClick={() => clientsQuery.refetch()}
          >
            <RefreshCw className={clientsQuery.isFetching ? 'animate-spin' : ''} />
          </Button>
        </div>
      </div>

      <div className="relative max-w-sm">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Buscar cliente por nombre…"
          className="pl-9"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {clientsQuery.isLoading ? (
        <p className="p-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : clientesFiltrados.length === 0 ? (
        <p className="p-6 text-center text-sm text-muted-foreground">
          {search.trim() ? 'No se encontraron clientes con ese criterio.' : 'Aún no tienes clientes registrados.'}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {clientesFiltrados.map((client) => (
            <div key={client.id} className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium">{client.nombre}</h3>
                <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                  {CLIENT_TYPE_LABELS[client.tipo]}
                </span>
              </div>
              <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Phone className="size-3.5" />
                {client.telefono}
              </p>
              <div className="mt-1">
                <Button variant="ghost" size="sm" onClick={() => openEdit(client)}>
                  <Pencil /> Editar
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>{editing ? 'Editar cliente' : 'Nuevo cliente'}</SheetTitle>
            <SheetDescription>
              {editing ? 'Actualiza los datos de este cliente.' : 'Registra un nuevo cliente comercial.'}
            </SheetDescription>
          </SheetHeader>
          <ClienteForm
            client={editing}
            onSubmit={(payload) =>
              editing ? updateMutation.mutate(payload) : createMutation.mutate(payload)
            }
            isSubmitting={activeMutation.isPending}
            error={mutationError}
          />
        </SheetContent>
      </Sheet>
    </div>
  )
}
