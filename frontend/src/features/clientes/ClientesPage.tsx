import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, RefreshCw, Search } from 'lucide-react'
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
import { dashboardApi } from '@/features/dashboard/api'
import type { RankingComercialItem } from '@/features/alertas/api'
import { pautasApi } from '@/features/contratos/api'
import { solicitudesApi } from '@/features/solicitudes/api'
import { clientsApi, type Client, type ClientInput } from './api'
import { ClienteForm } from './ClienteForm'
import { ClientCard } from './ClientCard'
import { ClienteFicha } from './ClienteFicha'

const CLIENTS_KEY = ['clients']
const PAUTAS_KEY = ['pautas']
const RANKING_KEY = ['dashboard', 'ranking']
const KANBAN_KEY = ['solicitudes-kanban']

const ESTADO_COMERCIAL_PRIORIDAD: Record<string, number> = {
  vencido: 0,
  atencion: 1,
  renovacion: 2,
  saludable: 3,
}

export function ClientesPage() {
  const queryClient = useQueryClient()
  const location = useLocation()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [sheetOpen, setSheetOpen] = useState(false)
  const [editing, setEditing] = useState<Client | null>(null)
  const [fichaClientId, setFichaClientId] = useState<string | null>(null)

  // Cross-module deep link (from Alertas' "Ver cliente", the ranking
  // list, or a future search result) — same navigation-state pattern
  // as Contratos' preselectClientId. Legacy's data-ficha-cliente opens
  // this same ficha from anywhere in the app, not just from Clientes.
  useEffect(() => {
    const state = location.state as { abrirFichaClientId?: string } | null
    if (state?.abrirFichaClientId) {
      setFichaClientId(state.abrirFichaClientId)
      navigate(location.pathname, { replace: true, state: null })
    }
  }, [location.state, location.pathname, navigate])

  const clientsQuery = useQuery({ queryKey: CLIENTS_KEY, queryFn: clientsApi.list })
  const pautasQuery = useQuery({ queryKey: PAUTAS_KEY, queryFn: pautasApi.list })
  const rankingQuery = useQuery({ queryKey: RANKING_KEY, queryFn: dashboardApi.ranking })
  const kanbanQuery = useQuery({ queryKey: KANBAN_KEY, queryFn: solicitudesApi.loadKanban })

  const rankingByClientId = useMemo(() => {
    const map = new Map<string, RankingComercialItem>()
    for (const item of rankingQuery.data ?? []) map.set(item.cliente.id, item)
    return map
  }, [rankingQuery.data])

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
      queryClient.invalidateQueries({ queryKey: RANKING_KEY })
      setSheetOpen(false)
      toast.success('Cliente actualizado.')
    },
  })

  const clientesFiltrados = useMemo(() => {
    const clientes = clientsQuery.data ?? []
    const termino = search.trim().toLowerCase()
    const filtrados = termino ? clientes.filter((c) => c.nombre.toLowerCase().includes(termino)) : clientes
    // Urgencia comercial primero — un cliente vencido no debería pesar
    // igual que uno saludable solo porque el grid los lista en el mismo
    // orden de inserción; "sin pauta" va al final porque no hay renovación
    // que se esté por perder, es prospección, no urgencia.
    return [...filtrados].sort((a, b) => {
      const pa = ESTADO_COMERCIAL_PRIORIDAD[rankingByClientId.get(a.id)?.estado_comercial ?? ''] ?? 4
      const pb = ESTADO_COMERCIAL_PRIORIDAD[rankingByClientId.get(b.id)?.estado_comercial ?? ''] ?? 4
      return pa !== pb ? pa - pb : a.nombre.localeCompare(b.nombre)
    })
  }, [clientsQuery.data, search, rankingByClientId])

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

  const fichaClient = fichaClientId ? (clientsQuery.data?.find((c) => c.id === fichaClientId) ?? null) : null
  const pautasFicha = (pautasQuery.data ?? [])
    .filter((p) => p.client_id === fichaClientId)
    .sort((a, b) => b.fecha_inicio.localeCompare(a.fecha_inicio))
  const pautaIdsFicha = new Set(pautasFicha.map((p) => p.id))
  // A solicitud belongs to this ficha either through its Pauta or, for one
  // received before a Pauta was known, through the client_id captured
  // directly at intake — otherwise a request like that would never show
  // up on the client's own ficha even though it names them as the sender.
  function esDeEsteCliente(s: { pauta_id: string | null; client_id: string | null }) {
    return (s.pauta_id !== null && pautaIdsFicha.has(s.pauta_id)) || s.client_id === fichaClientId
  }
  const pendientesFicha = (kanbanQuery.data?.pendientes ?? []).filter(esDeEsteCliente)
  const publicadasFicha = (kanbanQuery.data?.publicadas ?? [])
    .filter(esDeEsteCliente)
    .sort((a, b) => b.fecha_recepcion.localeCompare(a.fecha_recepcion))

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
            onClick={() => {
              clientsQuery.refetch()
              pautasQuery.refetch()
              rankingQuery.refetch()
            }}
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
            <ClientCard
              key={client.id}
              client={client}
              item={rankingByClientId.get(client.id)}
              onDetalle={() => setFichaClientId(client.id)}
              onEditar={() => openEdit(client)}
            />
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

      <ClienteFicha
        open={fichaClientId !== null}
        onOpenChange={(open) => !open && setFichaClientId(null)}
        client={fichaClient}
        item={fichaClientId ? rankingByClientId.get(fichaClientId) : undefined}
        pautasCliente={pautasFicha}
        solicitudesPendientes={pendientesFicha}
        solicitudesPublicadas={publicadasFicha}
        onEditar={() => {
          if (fichaClient) openEdit(fichaClient)
        }}
      />
    </div>
  )
}
