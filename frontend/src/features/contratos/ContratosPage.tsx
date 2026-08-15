import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Calendar, Pencil, Plus, RefreshCw, Search } from 'lucide-react'
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
import { formatFecha, formatMoneda } from '@/lib/format'
import { PAUTA_TIPO_LABELS, pautasApi, type Pauta, type PautaInput } from './api'
import { PautaForm } from './PautaForm'
import { cupoNivel, CUPO_BAR_COLOR } from './utils'

const PAUTAS_KEY = ['pautas']
const CLIENTS_KEY = ['clients']

export function ContratosPage() {
  const queryClient = useQueryClient()
  const location = useLocation()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
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

  const contratosFiltrados = useMemo(() => {
    const activos = (pautasQuery.data ?? [])
      .filter((p) => p.vigente)
      .sort((a, b) => a.fecha_fin.localeCompare(b.fecha_fin))
    const termino = search.trim().toLowerCase()
    if (!termino) return activos
    return activos.filter((p) => (clientsById.get(p.client_id) ?? '').toLowerCase().includes(termino))
  }, [pautasQuery.data, clientsById, search])

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
          <h1 className="text-lg font-semibold">Contratos activos</h1>
          <p className="text-sm text-muted-foreground">
            Cada pauta vigente, con su propio saldo — nunca se suman entre contratos
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

      <div className="relative max-w-sm">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Buscar por cliente…"
          className="pl-9"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {pautasQuery.isLoading ? (
        <p className="p-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : contratosFiltrados.length === 0 ? (
        <p className="p-6 text-center text-sm text-muted-foreground">
          {search.trim() ? 'No se encontraron contratos con ese criterio.' : 'No hay contratos vigentes.'}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {contratosFiltrados.map((pauta) => {
            const pct =
              pauta.publicaciones_contratadas > 0
                ? Math.round((pauta.publicaciones_restantes / pauta.publicaciones_contratadas) * 100)
                : 0
            const nivel = cupoNivel(pauta.publicaciones_restantes, pauta.publicaciones_contratadas, pauta.vigente)
            return (
              <div key={pauta.id} className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-medium">{clientsById.get(pauta.client_id) ?? '(cliente desconocido)'}</h3>
                  <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                    {PAUTA_TIPO_LABELS[pauta.tipo]}
                  </span>
                </div>
                <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Calendar className="size-3.5" />
                  {formatFecha(pauta.fecha_inicio)} – {formatFecha(pauta.fecha_fin)}
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
                  <Button variant="ghost" size="sm" onClick={() => openEdit(pauta)}>
                    <Pencil /> Editar
                  </Button>
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
