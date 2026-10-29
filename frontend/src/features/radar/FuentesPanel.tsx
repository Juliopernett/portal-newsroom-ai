import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Pause, Play, Plus, Search } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SelectNative } from '@/components/ui/select-native'
import { formatHoras, horasEnEspera } from '@/features/solicitudes/utils'
import { fuentesApi, type FuenteRadar, type ProbarFuente } from './api'

const FUENTES_KEY = ['radar-fuentes']

const INTERVALOS: { value: number; label: string }[] = [
  { value: 15, label: 'cada 15 min' },
  { value: 30, label: 'cada 30 min' },
  { value: 60, label: 'cada hora' },
  { value: 180, label: 'cada 3 horas' },
  { value: 360, label: 'cada 6 horas' },
  { value: 720, label: 'cada 12 horas' },
  { value: 1440, label: 'cada día' },
]

function FilaFuente({ fuente }: { fuente: FuenteRadar }) {
  const queryClient = useQueryClient()
  const editarMutation = useMutation({
    mutationFn: (cambios: Parameters<typeof fuentesApi.editar>[1]) =>
      fuentesApi.editar(fuente.id, cambios),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: FUENTES_KEY }),
    onError: (err) => toast.error(errorMessage(err)),
  })

  const opciones = INTERVALOS.some((i) => i.value === fuente.intervalo_minutos)
    ? INTERVALOS
    : [...INTERVALOS, { value: fuente.intervalo_minutos, label: `cada ${fuente.intervalo_minutos} min` }]

  return (
    <div className="flex flex-col gap-1 rounded-md border border-border p-2 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-medium">{fuente.name}</p>
          <p className="truncate text-xs text-muted-foreground">{fuente.url}</p>
        </div>
        <div className="flex items-center gap-2">
          <SelectNative
            className="h-8 w-auto text-xs"
            value={fuente.intervalo_minutos}
            disabled={editarMutation.isPending}
            onChange={(e) => editarMutation.mutate({ intervalo_minutos: Number(e.target.value) })}
          >
            {opciones.map((i) => (
              <option key={i.value} value={i.value}>
                {i.label}
              </option>
            ))}
          </SelectNative>
          <Button
            size="sm"
            variant={fuente.enabled ? 'secondary' : 'outline'}
            disabled={editarMutation.isPending}
            onClick={() => editarMutation.mutate({ enabled: !fuente.enabled })}
          >
            {fuente.enabled ? <Pause /> : <Play />}
            {fuente.enabled ? 'Activa' : 'Pausada'}
          </Button>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        {fuente.last_scan
          ? `Último escaneo ${formatHoras(horasEnEspera(fuente.last_scan))} · ${fuente.last_new_count} nuevas`
          : 'Nunca escaneada'}
        {` · máx. ${fuente.max_items} por escaneo, de los últimos ${fuente.max_age_days} días`}
      </p>
      {fuente.last_error && (
        <p className="text-xs text-destructive">
          Falló{fuente.errores_consecutivos > 1 ? ` (${fuente.errores_consecutivos} veces seguidas)` : ''}:{' '}
          {fuente.last_error}
        </p>
      )}
    </div>
  )
}

/** Fuentes del Radar: lista, pausar/activar, frecuencia y agregar una nueva con vista previa. */
export function FuentesPanel() {
  const queryClient = useQueryClient()
  const fuentesQuery = useQuery({ queryKey: FUENTES_KEY, queryFn: fuentesApi.listar })
  const [url, setUrl] = useState('')
  const [vistaPrevia, setVistaPrevia] = useState<ProbarFuente | null>(null)

  const probarMutation = useMutation({
    mutationFn: () => fuentesApi.probar(url.trim()),
    onSuccess: setVistaPrevia,
    onError: (err) => {
      setVistaPrevia(null)
      toast.error(errorMessage(err))
    },
  })
  const agregarMutation = useMutation({
    mutationFn: () => fuentesApi.crear(url.trim()),
    onSuccess: (fuente) => {
      queryClient.invalidateQueries({ queryKey: FUENTES_KEY })
      toast.success(`Fuente «${fuente.name}» agregada.`)
      setUrl('')
      setVistaPrevia(null)
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3">
      <div>
        <p className="font-medium">Fuentes del Radar</p>
        <p className="text-xs text-muted-foreground">
          Pega la dirección de una web (o de su feed RSS): se detecta el feed y ves las últimas notas
          antes de agregarla. El escaneo automático corre cada hora y solo consulta las fuentes a las
          que ya les toca.
        </p>
      </div>

      {fuentesQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <div className="flex flex-col gap-2">
          {(fuentesQuery.data ?? []).map((f) => (
            <FilaFuente key={f.id} fuente={f} />
          ))}
        </div>
      )}

      <div className="flex flex-col gap-2 border-t border-border pt-3">
        <div className="flex flex-wrap gap-2">
          <Input
            className="min-w-0 flex-1"
            placeholder="https://www.blogvallenato.com"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value)
              setVistaPrevia(null)
            }}
          />
          <Button
            variant="outline"
            disabled={url.trim().length < 4 || probarMutation.isPending}
            onClick={() => probarMutation.mutate()}
          >
            {probarMutation.isPending ? <Loader2 className="animate-spin" /> : <Search />}
            Probar
          </Button>
        </div>

        {vistaPrevia && (
          <div className="flex flex-col gap-2 rounded-md bg-muted/40 p-2 text-xs">
            <p className="font-medium text-foreground">{vistaPrevia.titulo}</p>
            <p className="break-all text-muted-foreground">{vistaPrevia.feed_url}</p>
            <ul className="list-disc pl-4 text-muted-foreground">
              {vistaPrevia.entradas.map((e) => (
                <li key={e.titulo}>{e.titulo}</li>
              ))}
            </ul>
            <Button
              size="sm"
              className="self-start"
              disabled={agregarMutation.isPending}
              onClick={() => agregarMutation.mutate()}
            >
              {agregarMutation.isPending ? <Loader2 className="animate-spin" /> : <Plus />}
              Agregar fuente
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
