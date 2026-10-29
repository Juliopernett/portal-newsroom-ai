import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, RefreshCw, Rss, ScanSearch, Search } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SelectNative } from '@/components/ui/select-native'
import { fuentesApi, radarApi } from './api'
import { FuentesPanel } from './FuentesPanel'
import { MetricasRadar } from './MetricasRadar'
import { RadarCandidateCard } from './RadarCandidateCard'

type FiltroEstado = 'todos' | 'nuevo' | 'guardado' | 'descartado' | 'procesado'

const FILTROS: { value: FiltroEstado; label: string }[] = [
  { value: 'todos', label: 'Todos' },
  { value: 'nuevo', label: 'Nuevos' },
  { value: 'guardado', label: 'Guardados' },
  { value: 'descartado', label: 'Descartados' },
  { value: 'procesado', label: 'Procesadas' },
]

export function RadarPage() {
  const [filtro, setFiltro] = useState<FiltroEstado>('todos')
  const [busqueda, setBusqueda] = useState('')
  const [fuente, setFuente] = useState('')
  const [mostrarFuentes, setMostrarFuentes] = useState(false)
  const [incluirAntiguos, setIncluirAntiguos] = useState(false)

  // Trae los candidatos una vez — igual que Solicitudes con su cola de
  // trabajo — y las pestañas/búsqueda/fuente se resuelven en cliente, sin
  // refetch por cada clic. Por defecto el backend solo manda los nuevos de los
  // últimos 30 días (más lo ya revisado): la lista no crece sin límite.
  const candidatosQuery = useQuery({
    queryKey: ['radar-candidatos', incluirAntiguos],
    queryFn: () => radarApi.listar(incluirAntiguos),
  })
  const fuentesQuery = useQuery({ queryKey: ['radar-fuentes'], queryFn: fuentesApi.listar })
  const queryClient = useQueryClient()

  // Al abrir "Procesadas" (y con "Actualizar Radar" estando ahí) se le pregunta
  // a WordPress si los borradores ya se publicaron — una sola petición.
  const { mutate: sincronizar } = useMutation({
    mutationFn: radarApi.sincronizarWordpress,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['radar-candidatos'] }),
  })
  useEffect(() => {
    if (filtro === 'procesado') sincronizar()
  }, [filtro, sincronizar])

  // "Escanear ahora": va a las fuentes y trae noticias nuevas. Es lo que
  // "Actualizar Radar" NO hace (este solo vuelve a leer lo ya guardado).
  const escanearMutation = useMutation({
    mutationFn: fuentesApi.escanear,
    onSuccess: (r) => {
      queryClient.invalidateQueries({ queryKey: ['radar-candidatos'] })
      queryClient.invalidateQueries({ queryKey: ['radar-fuentes'] })
      const conError = r.resultados.filter((x) => x.estado === 'error').length
      toast.success(
        r.nuevos_total > 0
          ? `${r.nuevos_total} noticia${r.nuevos_total === 1 ? '' : 's'} nueva${r.nuevos_total === 1 ? '' : 's'}.`
          : 'No hay noticias nuevas por ahora.',
      )
      if (conError > 0) {
        toast.error(`${conError} fuente${conError === 1 ? '' : 's'} con error — mira el panel Fuentes.`)
      }
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const candidatosData = candidatosQuery.data
  const candidatos = useMemo(() => candidatosData ?? [], [candidatosData])

  const nombresFuente = useMemo(
    () => new Map((fuentesQuery.data ?? []).map((f) => [f.id, f.name])),
    [fuentesQuery.data],
  )
  const fuentes = useMemo(
    () => Array.from(new Set(candidatos.map((c) => c.source))).sort(),
    [candidatos],
  )

  const busquedaTrim = busqueda.trim().toLowerCase()
  const visibles = candidatos.filter((c) => {
    if (filtro !== 'todos' && c.estado !== filtro) return false
    if (fuente && c.source !== fuente) return false
    if (
      busquedaTrim &&
      !c.title.toLowerCase().includes(busquedaTrim) &&
      !c.summary.toLowerCase().includes(busquedaTrim)
    ) {
      return false
    }
    return true
  })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">Radar Editorial</h1>
          <p className="text-sm text-muted-foreground">
            Lo que Discovery encontró — revisa, guarda o descarta.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setMostrarFuentes((v) => !v)}
            aria-pressed={mostrarFuentes}
          >
            <Rss /> Fuentes
          </Button>
          <Button
            variant="outline"
            size="sm"
            title="Vuelve a leer lo que ya está guardado. Para traer noticias nuevas usa «Escanear ahora»."
            onClick={() => {
              candidatosQuery.refetch()
              if (filtro === 'procesado') sincronizar()
            }}
            disabled={candidatosQuery.isFetching}
          >
            <RefreshCw className={candidatosQuery.isFetching ? 'animate-spin' : ''} />
            Actualizar Radar
          </Button>
          <Button
            size="sm"
            title="Consulta todas las fuentes activas ahora mismo"
            onClick={() => escanearMutation.mutate()}
            disabled={escanearMutation.isPending}
          >
            {escanearMutation.isPending ? <Loader2 className="animate-spin" /> : <ScanSearch />}
            Escanear ahora
          </Button>
        </div>
      </div>

      {mostrarFuentes && <FuentesPanel />}

      {!candidatosQuery.isLoading && <MetricasRadar candidatos={candidatos} />}

      <div className="flex flex-wrap items-center gap-2">
        {FILTROS.map((f) => (
          <Button
            key={f.value}
            type="button"
            size="sm"
            variant={filtro === f.value ? 'default' : 'secondary'}
            onClick={() => setFiltro(f.value)}
          >
            {f.label}
          </Button>
        ))}

        <div className="relative max-w-xs flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por titular o resumen…"
            className="pl-9"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </div>

        {fuentes.length > 1 && (
          <SelectNative
            className="h-9 w-auto max-w-[16rem] text-base sm:text-xs"
            value={fuente}
            onChange={(e) => setFuente(e.target.value)}
          >
            <option value="">Todas las fuentes</option>
            {fuentes.map((f) => (
              <option key={f} value={f}>
                {nombresFuente.get(f) ?? f}
              </option>
            ))}
          </SelectNative>
        )}

        <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={incluirAntiguos}
            onChange={(e) => setIncluirAntiguos(e.target.checked)}
          />
          Incluir nuevos de más de 30 días
        </label>
      </div>

      {candidatosQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : visibles.length === 0 ? (
        <p className="rounded-md border border-border bg-card p-4 text-center text-sm text-muted-foreground">
          {candidatos.length === 0
            ? 'Sin candidatos recientes — pulsa «Escanear ahora» para traer las últimas noticias.'
            : 'Ningún candidato coincide con este filtro.'}
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {visibles.map((candidato) => (
            <RadarCandidateCard
              key={candidato.id}
              candidato={candidato}
              nombreFuente={nombresFuente.get(candidato.source)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
