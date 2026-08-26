import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SelectNative } from '@/components/ui/select-native'
import { radarApi } from './api'
import { MetricasRadar } from './MetricasRadar'
import { RadarCandidateCard } from './RadarCandidateCard'

type FiltroEstado = 'todos' | 'nuevo' | 'guardado' | 'descartado'

const FILTROS: { value: FiltroEstado; label: string }[] = [
  { value: 'todos', label: 'Todos' },
  { value: 'nuevo', label: 'Nuevos' },
  { value: 'guardado', label: 'Guardados' },
  { value: 'descartado', label: 'Descartados' },
]

export function RadarPage() {
  const [filtro, setFiltro] = useState<FiltroEstado>('todos')
  const [busqueda, setBusqueda] = useState('')
  const [fuente, setFuente] = useState('')

  // Trae todos los candidatos una vez — igual que Solicitudes con su cola
  // de trabajo — y las pestañas/búsqueda/fuente se resuelven en cliente,
  // sin refetch por cada clic. El backend igual soporta `estado`/`q` como
  // filtros propios (ver app/api/routers/discovery.py), por si un
  // consumidor futuro los necesita.
  const candidatosQuery = useQuery({ queryKey: ['radar-candidatos'], queryFn: radarApi.listar })
  const candidatosData = candidatosQuery.data
  const candidatos = useMemo(() => candidatosData ?? [], [candidatosData])

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
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">Radar Editorial</h1>
          <p className="text-sm text-muted-foreground">
            Lo que Discovery encontró — revisa, guarda o descarta.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => candidatosQuery.refetch()}
          disabled={candidatosQuery.isFetching}
        >
          <RefreshCw className={candidatosQuery.isFetching ? 'animate-spin' : ''} />
          Actualizar Radar
        </Button>
      </div>

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
                {f}
              </option>
            ))}
          </SelectNative>
        )}
      </div>

      {candidatosQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : visibles.length === 0 ? (
        <p className="rounded-md border border-border bg-card p-4 text-center text-sm text-muted-foreground">
          {candidatos.length === 0
            ? 'Sin candidatos todavía — corre "python -m scripts.descubrir_noticias" y actualiza el Radar.'
            : 'Ningún candidato coincide con este filtro.'}
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {visibles.map((candidato) => (
            <RadarCandidateCard key={candidato.id} candidato={candidato} />
          ))}
        </div>
      )}
    </div>
  )
}
