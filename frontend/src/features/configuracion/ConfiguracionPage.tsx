import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RefreshCw, X } from 'lucide-react'
import { toast } from 'sonner'

import { ApiError, errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { formatMoneda } from '@/lib/format'
import { planesPautaApi, type PlanPauta, type PlanPautaInput } from './api'
import { PlanPautaForm } from './PlanPautaForm'

const PLANES_KEY = ['planes-pauta']

export function ConfiguracionPage() {
  const queryClient = useQueryClient()
  const [sheetOpen, setSheetOpen] = useState(false)
  const [editing, setEditing] = useState<PlanPauta | null>(null)

  const planesQuery = useQuery({ queryKey: PLANES_KEY, queryFn: planesPautaApi.list })
  const planes = planesQuery.data ?? []

  const createMutation = useMutation({
    mutationFn: planesPautaApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PLANES_KEY })
      setSheetOpen(false)
      toast.success('Plan creado.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (payload: PlanPautaInput) => planesPautaApi.update(editing!.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PLANES_KEY })
      setSheetOpen(false)
      toast.success('Plan actualizado.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: planesPautaApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PLANES_KEY })
      toast.success('Plan eliminado.')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  function openNew() {
    setEditing(null)
    createMutation.reset()
    updateMutation.reset()
    setSheetOpen(true)
  }

  function openEdit(plan: PlanPauta) {
    setEditing(plan)
    createMutation.reset()
    updateMutation.reset()
    setSheetOpen(true)
  }

  const activeMutation = editing ? updateMutation : createMutation
  const mutationError = activeMutation.error instanceof ApiError ? activeMutation.error.message : null
  const siguienteOrden = planes.length > 0 ? Math.max(...planes.map((p) => p.orden)) + 1 : 0

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">Configuración</h1>
          <p className="text-sm text-muted-foreground">
            Planes de Pauta — cantidad de publicaciones, valor y vigencia que se ofrecen al registrar
            un contrato.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={openNew}>
            <Plus /> Nuevo plan
          </Button>
          <Button
            variant="outline"
            size="icon"
            aria-label="Actualizar"
            onClick={() => planesQuery.refetch()}
          >
            <RefreshCw className={planesQuery.isFetching ? 'animate-spin' : ''} />
          </Button>
        </div>
      </div>

      <div className="flex flex-col divide-y divide-border rounded-lg border border-border">
        {planesQuery.isLoading ? (
          <p className="p-6 text-center text-sm text-muted-foreground">Cargando…</p>
        ) : planes.length === 0 ? (
          <p className="p-6 text-center text-sm text-muted-foreground">
            Todavía no hay planes configurados.
          </p>
        ) : (
          planes.map((plan) => (
            <div key={plan.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
              <span className="w-full min-w-0 truncate sm:w-auto sm:flex-1">{plan.nombre}</span>
              <span className="shrink-0 text-muted-foreground sm:w-32">
                {plan.cantidad_publicaciones} publ.
              </span>
              <span className="shrink-0 text-muted-foreground sm:w-24">{plan.dias_vigencia} días</span>
              <span className="shrink-0 font-medium sm:w-28 sm:text-right">{formatMoneda(plan.valor)}</span>
              <span className="ml-auto flex shrink-0 items-center gap-1">
                <Button variant="ghost" size="sm" onClick={() => openEdit(plan)}>
                  <Pencil /> Editar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-danger hover:text-danger"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(plan.id)}
                >
                  <X /> Eliminar
                </Button>
              </span>
            </div>
          ))
        )}
      </div>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>{editing ? 'Editar plan' : 'Nuevo plan'}</SheetTitle>
            <SheetDescription>
              {editing
                ? 'Actualiza los datos de este plan.'
                : 'Agrega un plan al catálogo de Pautas.'}
            </SheetDescription>
          </SheetHeader>
          <PlanPautaForm
            plan={editing}
            siguienteOrden={siguienteOrden}
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
