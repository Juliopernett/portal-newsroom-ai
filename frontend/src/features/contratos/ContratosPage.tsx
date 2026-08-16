import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Calendar, Inbox, Pencil, Plus, RefreshCw, Search } from 'lucide-react'
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
import { clientsApi } from '@/features/clientes/api'
import { diasHasta, formatFecha, formatMoneda } from '@/lib/format'
import { PAUTA_TIPO_LABELS, pautasApi, type Pauta, type PautaInput } from './api'
import { PautaForm } from './PautaForm'
import { cupoNivel, CUPO_BAR_COLOR } from './utils'

type EstadoFiltro = 'vigentes' | 'vencidos' | 'todos'

const ESTADO_TABS: { id: EstadoFiltro; label: string }[] = [
  { id: 'vigentes', label: 'Vigentes' },
  { id: 'vencidos', label: 'Vencidos' },
  { id: 'todos', label: 'Todos' },
]

// Same 7/15/30 urgency the Radar de Renovaciones already uses in Alertas —
// reused here so "vence pronto" reads the same way in both places instead
// of only being visible if you happen to check Alertas.
function venceProntoBadge(dias: number): { label: string; className: string } | null {
  if (dias < 0 || dias > 30) return null
  if (dias <= 7) return { label: `Vence en ${dias}d`, className: 'bg-danger-bg text-danger' }
  if (dias <= 15) return { label: `Vence en ${dias}d`, className: 'bg-warning-bg text-warning' }
  return { label: `Vence en ${dias}d`, className: 'bg-muted text-muted-foreground' }
}

const PAUTAS_KEY = ['pautas']
const CLIENTS_KEY = ['clients']

export function ContratosPage() {
  const queryClient = useQueryClient()
  const location = useLocation()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [estadoFiltro, setEstadoFiltro] = useState<EstadoFiltro>('vigentes')
  const [sheetOpen, setSheetOpen] = useState(false)
  const [editing, setEditing] = useState<Pauta | null>(null)
  const [preselectClientId, setPreselectClientId] = useState<string | undefined>()

  const pautasQuery = useQuery({ queryKey: PAUTAS_KEY, queryFn: pautasApi.list })

  // Cross-module deep links arrive via navigation state, then get
  // cleared — matches the legacy app's data-preselect-client /
  // data-edit-pauta. preselectClientId comes from Alertas'
  // "Renovar"/"Reactivar"; editPautaId comes from a client's ficha
  // ("Editar" on one specific pauta in their historial) — this one
  // needs the unfiltered pautasQuery data since a client's history can
  // include pautas that are no longer vigente (and so wouldn't be in
  // contratosFiltrados).
  useEffect(() => {
    const state = location.state as { preselectClientId?: string; editPautaId?: string } | null
    if (state?.preselectClientId) {
      setEditing(null)
      setPreselectClientId(state.preselectClientId)
      setSheetOpen(true)
      navigate(location.pathname, { replace: true, state: null })
    } else if (state?.editPautaId && pautasQuery.data) {
      const pauta = pautasQuery.data.find((p) => p.id === state.editPautaId)
      if (pauta) {
        setEditing(pauta)
        setPreselectClientId(undefined)
        setSheetOpen(true)
      }
      navigate(location.pathname, { replace: true, state: null })
    }
  }, [location.state, location.pathname, navigate, pautasQuery.data])
  const clientsQuery = useQuery({ queryKey: CLIENTS_KEY, queryFn: clientsApi.list })

  const clientsById = useMemo(() => {
    const map = new Map<string, string>()
    for (const c of clientsQuery.data ?? []) map.set(c.id, c.nombre)
    return map
  }, [clientsQuery.data])

  const createMutation = useMutation({
    mutationFn: pautasApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PAUTAS_KEY })
      setSheetOpen(false)
      toast.success('Pauta creada.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (payload: PautaInput) => pautasApi.update(editing!.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PAUTAS_KEY })
      setSheetOpen(false)
      toast.success('Pauta actualizada.')
    },
  })

  const todasPautas = pautasQuery.data ?? []
  const vigentesCount = todasPautas.filter((p) => p.vigente).length
  const vencidasCount = todasPautas.filter((p) => !p.vigente).length

  const contratosFiltrados = useMemo(() => {
    const porEstado = todasPautas
      .filter((p) => {
        if (estadoFiltro === 'vigentes') return p.vigente
        if (estadoFiltro === 'vencidos') return !p.vigente
        return true
      })
      .sort((a, b) =>
        estadoFiltro === 'vigentes'
          ? a.fecha_fin.localeCompare(b.fecha_fin) // vigentes: próximas a vencer primero
          : b.fecha_fin.localeCompare(a.fecha_fin), // vencidos/todos: más recientes primero
      )
    const termino = search.trim().toLowerCase()
    if (!termino) return porEstado
    return porEstado.filter((p) => (clientsById.get(p.client_id) ?? '').toLowerCase().includes(termino))
  }, [todasPautas, clientsById, search, estadoFiltro])

  function openNew() {
    setEditing(null)
    setPreselectClientId(undefined)
    createMutation.reset()
    updateMutation.reset()
    setSheetOpen(true)
  }

  function openEdit(pauta: Pauta) {
    setEditing(pauta)
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
          <h1 className="text-lg font-semibold">Contratos</h1>
          <p className="text-sm text-muted-foreground">
            Cada pauta con su propio saldo — nunca se suman entre contratos
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={openNew}>
            <Plus /> Nueva pauta
          </Button>
          <Button
            variant="outline"
            size="icon"
            aria-label="Actualizar"
            onClick={() => {
              pautasQuery.refetch()
              clientsQuery.refetch()
            }}
          >
            <RefreshCw className={pautasQuery.isFetching ? 'animate-spin' : ''} />
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Estado del contrato">
          {ESTADO_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={estadoFiltro === tab.id}
              onClick={() => setEstadoFiltro(tab.id)}
              className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                estadoFiltro === tab.id
                  ? 'border-brand bg-brand/10 text-foreground'
                  : 'border-border bg-card text-muted-foreground hover:bg-accent'
              }`}
            >
              {tab.label}
              <span className="text-xs text-muted-foreground">
                {tab.id === 'vigentes' ? vigentesCount : tab.id === 'vencidos' ? vencidasCount : todasPautas.length}
              </span>
            </button>
          ))}
        </div>
        <div className="relative max-w-sm flex-1 sm:flex-none">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por cliente…"
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {pautasQuery.isLoading ? (
        <p className="p-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : contratosFiltrados.length === 0 ? (
        <p className="p-6 text-center text-sm text-muted-foreground">
          {search.trim() ? 'No se encontraron contratos con ese criterio.' : 'No hay contratos en este estado.'}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {contratosFiltrados.map((pauta) => {
            const pct =
              pauta.publicaciones_contratadas > 0
                ? Math.round((pauta.publicaciones_restantes / pauta.publicaciones_contratadas) * 100)
                : 0
            const nivel = cupoNivel(pauta.publicaciones_restantes, pauta.publicaciones_contratadas, pauta.vigente)
            const badge = pauta.vigente ? venceProntoBadge(diasHasta(pauta.fecha_fin)) : null
            return (
              <div key={pauta.id} className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4">
                <div className="flex items-start justify-between gap-2">
                  <button
                    type="button"
                    className="font-medium underline-offset-2 hover:underline"
                    onClick={() =>
                      navigate('/clientes', { state: { abrirFichaClientId: pauta.client_id } })
                    }
                  >
                    {clientsById.get(pauta.client_id) ?? '(cliente desconocido)'}
                  </button>
                  <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                    {PAUTA_TIPO_LABELS[pauta.tipo]}
                  </span>
                </div>
                <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Calendar className="size-3.5" />
                  {formatFecha(pauta.fecha_inicio)} – {formatFecha(pauta.fecha_fin)}
                  {badge && (
                    <span className={`ml-1 rounded-full px-1.5 py-0.5 text-xs font-medium ${badge.className}`}>
                      {badge.label}
                    </span>
                  )}
                </p>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={`h-full ${CUPO_BAR_COLOR[nivel]}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <p className="text-sm">
                  <strong>{pauta.publicaciones_restantes}</strong> de {pauta.publicaciones_contratadas}{' '}
                  publicaciones disponibles
                </p>
                <div className="mt-1 flex items-center justify-between">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium">{formatMoneda(pauta.valor_pagado)}</span>
                    <span className="text-xs text-muted-foreground" title="Peso comercial — uso interno">
                      Peso {formatMoneda(pauta.peso_comercial)}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    {pauta.vigente && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          navigate('/solicitudes', { state: { prefillClientId: pauta.client_id } })
                        }
                      >
                        <Inbox /> Registrar
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => openEdit(pauta)}>
                      <Pencil /> Editar
                    </Button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>{editing ? 'Editar pauta' : 'Nueva pauta'}</SheetTitle>
            <SheetDescription>
              {editing ? 'Actualiza los datos de este contrato.' : 'Registra un nuevo contrato para un cliente.'}
            </SheetDescription>
          </SheetHeader>
          <PautaForm
            pauta={editing}
            clients={clientsQuery.data ?? []}
            preselectClientId={preselectClientId}
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
