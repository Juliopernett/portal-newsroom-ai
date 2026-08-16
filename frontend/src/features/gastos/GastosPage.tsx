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
import { otrosIngresosApi, type OtroIngreso, type OtroIngresoInput } from './otrosIngresosApi'
import { OtroIngresoForm } from './OtroIngresoForm'

const GASTOS_KEY = ['gastos']
const OTROS_INGRESOS_KEY = ['otros-ingresos']

type FinanzasTab = 'gastos' | 'ingresos'

function GastosPanel() {
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
        <p className="text-sm text-muted-foreground">
          Gastos operativos — alimentan la rentabilidad mensual del Dashboard
        </p>
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
            <div key={gasto.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
              <span className="w-full min-w-0 truncate sm:w-auto sm:flex-1">{gasto.descripcion}</span>
              <span className="shrink-0 text-muted-foreground sm:w-24">{formatFecha(gasto.fecha)}</span>
              <span className="shrink-0 font-medium sm:w-28 sm:text-right">{formatMoneda(gasto.valor)}</span>
              <span className="ml-auto flex shrink-0 items-center gap-1">
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

function OtrosIngresosPanel() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [sheetOpen, setSheetOpen] = useState(false)
  const [editing, setEditing] = useState<OtroIngreso | null>(null)

  const ingresosQuery = useQuery({ queryKey: OTROS_INGRESOS_KEY, queryFn: otrosIngresosApi.list })

  const createMutation = useMutation({
    mutationFn: otrosIngresosApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: OTROS_INGRESOS_KEY })
      setSheetOpen(false)
      toast.success('Ingreso registrado.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (payload: OtroIngresoInput) => otrosIngresosApi.update(editing!.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: OTROS_INGRESOS_KEY })
      setSheetOpen(false)
      toast.success('Ingreso actualizado.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: otrosIngresosApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: OTROS_INGRESOS_KEY })
      toast.success('Ingreso eliminado.')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const ingresosFiltrados = useMemo(() => {
    const ingresos = ingresosQuery.data ?? []
    const ordenados = [...ingresos].sort((a, b) => b.fecha_cobro.localeCompare(a.fecha_cobro))
    const termino = search.trim().toLowerCase()
    if (!termino) return ordenados
    return ordenados.filter((i) => i.origen.toLowerCase().includes(termino))
  }, [ingresosQuery.data, search])

  function openNew() {
    setEditing(null)
    createMutation.reset()
    updateMutation.reset()
    setSheetOpen(true)
  }

  function openEdit(ingreso: OtroIngreso) {
    setEditing(ingreso)
    createMutation.reset()
    updateMutation.reset()
    setSheetOpen(true)
  }

  const activeMutation = editing ? updateMutation : createMutation
  const mutationError = activeMutation.error instanceof ApiError ? activeMutation.error.message : null

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          Ingresos que no vienen de una pauta (Facebook, AdSense…) — también suman en la
          rentabilidad mensual del Dashboard
        </p>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={openNew}>
            <Plus /> Nuevo ingreso
          </Button>
          <Button
            variant="outline"
            size="icon"
            aria-label="Actualizar"
            onClick={() => ingresosQuery.refetch()}
          >
            <RefreshCw className={ingresosQuery.isFetching ? 'animate-spin' : ''} />
          </Button>
        </div>
      </div>

      <div className="relative max-w-sm">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Buscar por origen…"
          className="pl-9"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="flex flex-col divide-y divide-border rounded-lg border border-border">
        {ingresosQuery.isLoading ? (
          <p className="p-6 text-center text-sm text-muted-foreground">Cargando…</p>
        ) : ingresosFiltrados.length === 0 ? (
          <p className="p-6 text-center text-sm text-muted-foreground">
            {search.trim()
              ? 'No se encontraron ingresos con ese criterio.'
              : 'Todavía no hay ingresos registrados.'}
          </p>
        ) : (
          ingresosFiltrados.map((ingreso) => (
            <div key={ingreso.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
              <span className="w-full min-w-0 truncate sm:w-auto sm:flex-1">{ingreso.origen}</span>
              {ingreso.monto_usd && (
                <span className="shrink-0 text-muted-foreground sm:w-20">
                  US${Number(ingreso.monto_usd).toLocaleString('en-US', { maximumFractionDigits: 2 })}
                </span>
              )}
              <span className="shrink-0 text-muted-foreground sm:w-24">{formatFecha(ingreso.fecha_cobro)}</span>
              <span className="shrink-0 font-medium sm:w-28 sm:text-right">{formatMoneda(ingreso.monto)}</span>
              <span className="ml-auto flex shrink-0 items-center gap-1">
                <Button variant="ghost" size="sm" onClick={() => openEdit(ingreso)}>
                  <Pencil /> Editar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-danger hover:text-danger"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(ingreso.id)}
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
            <SheetTitle>{editing ? 'Editar ingreso' : 'Nuevo ingreso'}</SheetTitle>
            <SheetDescription>
              {editing
                ? 'Actualiza los datos de este ingreso.'
                : 'Registra un ingreso recibido fuera de una pauta.'}
            </SheetDescription>
          </SheetHeader>
          <OtroIngresoForm
            ingreso={editing}
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

export function GastosPage() {
  const [tab, setTab] = useState<FinanzasTab>('gastos')

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold">Gastos e ingresos</h1>
      </div>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Tipo de movimiento">
        {(
          [
            { id: 'gastos', label: 'Gastos' },
            { id: 'ingresos', label: 'Otros ingresos' },
          ] as const
        ).map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors ${
              tab === t.id
                ? 'border-brand bg-brand/10 text-foreground'
                : 'border-border bg-card text-muted-foreground hover:bg-accent'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'gastos' ? <GastosPanel /> : <OtrosIngresosPanel />}
    </div>
  )
}
