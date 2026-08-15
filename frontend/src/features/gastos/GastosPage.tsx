import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RefreshCw, Search, X } from 'lucide-react'
import { toast } from 'sonner'

import { ApiError, errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { formatFecha, formatMoneda } from '@/lib/format'
import { gastosApi, type Gasto, type GastoInput } from './api'
import { GastoForm } from './GastoForm'

const GASTOS_KEY = ['gastos']

export function GastosPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [sheetOpen, setSheetOpen] = useState(false)
  const [editing, setEditing] = useState<Gasto | null>(null)

  const gastosQuery = useQuery({ queryKey: GASTOS_KEY, queryFn: gastosApi.list })

  const createMutation = useMutation({
    mutationFn: gastosApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GASTOS_KEY })
      setSheetOpen(false)
      toast.success('Gasto registrado.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (payload: GastoInput) => gastosApi.update(editing!.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GASTOS_KEY })
      setSheetOpen(false)
      toast.success('Gasto actualizado.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: gastosApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GASTOS_KEY })
      toast.success('Gasto eliminado.')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const gastosFiltrados = useMemo(() => {
    const gastos = gastosQuery.data ?? []
    const ordenados = [...gastos].sort((a, b) => b.fecha.localeCompare(a.fecha))
    const termino = search.trim().toLowerCase()
    if (!termino) return ordenados
    return ordenados.filter((g) => g.descripcion.toLowerCase().includes(termino))
  }, [gastosQuery.data, search])

  function openNew() {
    setEditing(null)
    createMutation.reset()
    updateMutation.reset()
    setSheetOpen(true)
  }

  function openEdit(gasto: Gasto) {
    setEditing(gasto)
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
          <h1 className="text-lg font-semibold">Gastos</h1>
          <p className="text-sm text-muted-foreground">
            Gastos operativos — alimentan la rentabilidad mensual del Dashboard
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={openNew}>
            <Plus /> Nuevo gasto
          </Button>
          <Button
            variant="outline"
            size="icon"
            aria-label="Actualizar"
            onClick={() => gastosQuery.refetch()}
          >
            <RefreshCw className={gastosQuery.isFetching ? 'animate-spin' : ''} />
          </Button>
        </div>
      </div>

      <div className="relative max-w-sm">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Buscar por descripción…"
          className="pl-9"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="flex flex-col divide-y divide-border rounded-lg border border-border">
        {gastosQuery.isLoading ? (
          <p className="p-6 text-center text-sm text-muted-foreground">Cargando…</p>
        ) : gastosFiltrados.length === 0 ? (
          <p className="p-6 text-center text-sm text-muted-foreground">
            {search.trim() ? 'No se encontraron gastos con ese criterio.' : 'Todavía no hay gastos registrados.'}
          </p>
        ) : (
          gastosFiltrados.map((gasto) => (
            <div key={gasto.id} className="flex items-center gap-4 px-4 py-3 text-sm">
              <span className="flex-1 truncate">{gasto.descripcion}</span>
              <span className="w-24 shrink-0 text-muted-foreground">{formatFecha(gasto.fecha)}</span>
              <span className="w-28 shrink-0 text-right font-medium">{formatMoneda(gasto.valor)}</span>
              <span className="flex shrink-0 items-center gap-1">
                <Button variant="ghost" size="sm" onClick={() => openEdit(gasto)}>
                  <Pencil /> Editar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-danger hover:text-danger"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(gasto.id)}
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
            <SheetTitle>{editing ? 'Editar gasto' : 'Nuevo gasto'}</SheetTitle>
            <SheetDescription>
              {editing ? 'Actualiza los datos de este gasto.' : 'Registra un nuevo gasto operativo.'}
            </SheetDescription>
          </SheetHeader>
          <GastoForm
            gasto={editing}
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
