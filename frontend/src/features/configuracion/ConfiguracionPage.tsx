import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RefreshCw, Upload, X } from 'lucide-react'
import { toast } from 'sonner'

import { ApiError, errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SelectNative } from '@/components/ui/select-native'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { formatMoneda } from '@/lib/format'
import { identidadApi, LOGO_URL, type IdentidadComercialInput } from '@/features/identidad/api'
import { IdentidadForm } from '@/features/identidad/IdentidadForm'
import { aiConfiguracionApi, type AIConfiguracionInput, type ProveedorIA } from '@/features/ia/api'
import { planesPautaApi, type PlanPauta, type PlanPautaInput } from './api'
import { PlanPautaForm } from './PlanPautaForm'

const PLANES_KEY = ['planes-pauta']
const IDENTIDAD_KEY = ['identidad-comercial']
const AI_CONFIGURACION_KEY = ['ai-configuracion']

type ConfiguracionTab = 'planes' | 'identidad' | 'ia'

function PlanesPautaPanel() {
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
        <p className="text-sm text-muted-foreground">
          Cantidad de publicaciones, valor y vigencia que se ofrecen al registrar un contrato.
        </p>
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

function IdentidadPanel() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [logoCacheBuster, setLogoCacheBuster] = useState(0)

  const identidadQuery = useQuery({ queryKey: IDENTIDAD_KEY, queryFn: identidadApi.get })
  const identidad = identidadQuery.data ?? null

  const saveMutation = useMutation({
    mutationFn: (payload: IdentidadComercialInput) => identidadApi.save(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: IDENTIDAD_KEY })
      toast.success('Identidad comercial guardada.')
    },
  })

  const uploadLogoMutation = useMutation({
    mutationFn: (file: File) => identidadApi.uploadLogo(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: IDENTIDAD_KEY })
      setLogoCacheBuster((v) => v + 1)
      toast.success('Logo actualizado.')
      if (fileInputRef.current) fileInputRef.current.value = ''
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const saveError = saveMutation.error instanceof ApiError ? saveMutation.error.message : null

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-muted-foreground">
        Datos del medio que aparecen en el encabezado y cierre de los informes PDF entregados a
        clientes — no pertenecen a ningún Cliente ni Pauta en particular.
      </p>

      {identidadQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <>
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium">Logo</span>
            <div className="flex items-center gap-3">
              {identidad?.tiene_logo ? (
                <img
                  src={`${LOGO_URL}?v=${logoCacheBuster}`}
                  alt="Logo comercial"
                  className="size-16 rounded-md border border-border object-contain p-1"
                />
              ) : (
                <div className="flex size-16 items-center justify-center rounded-md border border-dashed border-border text-xs text-muted-foreground">
                  Sin logo
                </div>
              )}
              <div className="flex items-center gap-2">
                <Upload className="size-4 shrink-0 text-muted-foreground" />
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  disabled={!identidad || uploadLogoMutation.isPending}
                  className="text-base sm:text-xs"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) uploadLogoMutation.mutate(file)
                  }}
                />
                {uploadLogoMutation.isPending && (
                  <span className="text-xs text-muted-foreground">Subiendo…</span>
                )}
              </div>
            </div>
            {!identidad && (
              <p className="text-xs text-muted-foreground">
                Guarda primero los datos de abajo para poder subir el logo.
              </p>
            )}
          </div>

          <IdentidadForm
            identidad={identidad}
            onSubmit={(payload) => saveMutation.mutate(payload)}
            isSubmitting={saveMutation.isPending}
            error={saveError}
          />
        </>
      )}
    </div>
  )
}

const PROVEEDORES_IA: { value: ProveedorIA; label: string }[] = [
  { value: 'anthropic', label: 'Anthropic (Claude)' },
  { value: 'openrouter', label: 'OpenRouter' },
]

function IAPanel() {
  const queryClient = useQueryClient()
  const configuracionQuery = useQuery({ queryKey: AI_CONFIGURACION_KEY, queryFn: aiConfiguracionApi.get })
  const configuracion = configuracionQuery.data

  const [proveedor, setProveedor] = useState<ProveedorIA>('anthropic')
  const [modelo, setModelo] = useState('')
  // La consulta trae el default vigente (Anthropic + Claude Opus 5) aunque
  // nunca se haya guardado nada — sincronizamos el formulario una sola vez
  // cuando llega, sin pisar lo que el operador ya esté escribiendo después.
  useEffect(() => {
    if (configuracion) {
      setProveedor(configuracion.proveedor)
      setModelo(configuracion.modelo)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configuracion?.proveedor, configuracion?.modelo])

  const saveMutation = useMutation({
    mutationFn: (payload: AIConfiguracionInput) => aiConfiguracionApi.save(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: AI_CONFIGURACION_KEY })
      toast.success('Configuración de IA guardada.')
    },
  })

  const saveError = saveMutation.error instanceof ApiError ? saveMutation.error.message : null

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Proveedor y modelo que usa la preparación editorial con IA al crear un borrador de
        WordPress (título, entradilla, cuerpo, categoría y etiquetas). La API key
        correspondiente (<code>ANTHROPIC_API_KEY</code> u <code>OPENROUTER_API_KEY</code>) se
        configura aparte, en el servidor — aquí solo se elige cuál usar. Si la IA falla o no
        tiene crédito, el borrador se sigue creando igual con el texto original.
      </p>

      {configuracionQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <form
          className="flex max-w-md flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            saveMutation.mutate({ proveedor, modelo })
          }}
        >
          <label className="flex flex-col gap-1 text-sm">
            Proveedor
            <SelectNative
              value={proveedor}
              onChange={(e) => setProveedor(e.target.value as ProveedorIA)}
            >
              {PROVEEDORES_IA.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </SelectNative>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Modelo
            <Input
              required
              placeholder={proveedor === 'anthropic' ? 'claude-opus-5' : 'deepseek/deepseek-chat'}
              value={modelo}
              onChange={(e) => setModelo(e.target.value)}
            />
          </label>
          {saveError && <p className="text-sm text-danger">{saveError}</p>}
          <Button type="submit" disabled={saveMutation.isPending} className="self-start">
            {saveMutation.isPending ? 'Guardando…' : 'Guardar'}
          </Button>
        </form>
      )}
    </div>
  )
}

export function ConfiguracionPage() {
  const [tab, setTab] = useState<ConfiguracionTab>('planes')

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold">Configuración</h1>
      </div>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Sección de configuración">
        {(
          [
            { id: 'planes', label: 'Planes de Pauta' },
            { id: 'identidad', label: 'Identidad comercial' },
            { id: 'ia', label: 'IA' },
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

      {tab === 'planes' ? <PlanesPautaPanel /> : tab === 'identidad' ? <IdentidadPanel /> : <IAPanel />}
    </div>
  )
}
