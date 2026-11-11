import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Minus, Pin, RefreshCw, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SelectNative } from '@/components/ui/select-native'
import { chartApi, type FilaChart, type FilaEdicion } from './chartApi'

const KEY = ['chart-vallenato']
const KEY_CANALES = ['chart-vallenato', 'canales']
const KEY_EDICIONES = ['chart-vallenato', 'ediciones']
const num = (n: number) => n.toLocaleString('es-CO')
const normalizar = (s: string) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

function Tendencia({ fila }: { fila: Pick<FilaChart | FilaEdicion, 'tendencia'> }) {
  if (fila.tendencia === 'sube') return <ArrowUp className="size-4 text-success" aria-label="Sube" />
  if (fila.tendencia === 'baja') return <ArrowDown className="size-4 text-danger" aria-label="Baja" />
  if (fila.tendencia === 'nuevo')
    return <span className="text-[10px] font-bold text-brand">NUEVO</span>
  if (fila.tendencia === 'igual') return <Minus className="size-4 text-muted-foreground" aria-label="Igual" />
  return <span className="text-xs text-muted-foreground">—</span>
}


// Edición semanal: se cierra el viernes a medianoche (hora de Colombia). Queda en
// borrador para que el editor la revise (excluir / fijar abajo) y la publique.
function EdicionesSection() {
  const qc = useQueryClient()
  const lista = useQuery({ queryKey: KEY_EDICIONES, queryFn: chartApi.ediciones })
  const ultima = lista.data?.[0]
  const detalle = useQuery({
    queryKey: [...KEY_EDICIONES, ultima?.semana_fin],
    queryFn: () => chartApi.edicion(ultima!.semana_fin),
    enabled: !!ultima,
  })
  const refrescar = () => qc.invalidateQueries({ queryKey: KEY_EDICIONES })
  const regenerar = useMutation({
    mutationFn: (semana: string) => chartApi.regenerarEdicion(semana),
    onSuccess: () => {
      refrescar()
      toast.success('Borrador recalculado.')
    },
    onError: (e) => toast.error(errorMessage(e)),
  })
  const publicar = useMutation({
    mutationFn: (semana: string) => chartApi.publicarEdicion(semana),
    onSuccess: () => {
      refrescar()
      toast.success('Edición publicada.')
    },
    onError: (e) => toast.error(errorMessage(e)),
  })
  const ed = detalle.data

  return (
    <section className="flex flex-col gap-2 rounded-lg border border-border p-3">
      <h3 className="text-sm font-semibold">Edición semanal (cierre del viernes)</h3>
      {lista.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : !ultima ? (
        <p className="text-sm text-muted-foreground">
          Aún no hay ediciones. El primer cierre (viernes a medianoche) solo fija la línea base; la
          primera edición sale al cierre siguiente.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm">
              Semana cerrada el <strong>{ultima.semana_fin}</strong> ·{' '}
              <span className={ultima.estado === 'publicada' ? 'text-success' : 'text-warning'}>
                {ultima.estado === 'publicada' ? 'Publicada' : 'Borrador por revisar'}
              </span>
              {ultima.sin_base > 0 && (
                <span className="text-muted-foreground">
                  {' '}
                  · {ultima.sin_base} videos sin base de comparación (no entran)
                </span>
              )}
            </p>
            {ultima.estado === 'borrador' && (
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={regenerar.isPending}
                  onClick={() => regenerar.mutate(ultima.semana_fin)}
                >
                  Recalcular borrador
                </Button>
                <Button size="sm" disabled={publicar.isPending} onClick={() => publicar.mutate(ultima.semana_fin)}>
                  Publicar edición
                </Button>
              </div>
            )}
          </div>
          <ol className="flex flex-col gap-1">
            {ed?.filas_detalle.map((f) => (
              <li key={f.video_id} className="flex items-center gap-3 rounded-lg border border-border p-2 text-sm">
                <span className="w-6 text-center text-base font-bold text-brand">{f.posicion}</span>
                <Tendencia fila={f} />
                <div className="min-w-0 flex-1">
                  <a className="block truncate font-medium hover:underline" href={f.url} target="_blank" rel="noopener">
                    {f.titulo}
                  </a>
                  <p className="text-xs text-muted-foreground">
                    {f.artista ?? 'Sin artista'} · +{num(f.vistas_semana)} en la semana · {num(f.vistas_totales)} en total
                  </p>
                </div>
                {f.fijado && <Pin className="size-4 text-brand" aria-label="Fijado" />}
              </li>
            ))}
          </ol>
          {lista.data && lista.data.length > 1 && (
            <p className="text-xs text-muted-foreground">
              Anteriores: {lista.data.slice(1, 6).map((e) => `${e.semana_fin} (${e.estado})`).join(' · ')}
            </p>
          )}
        </>
      )}
    </section>
  )
}

// El chart se calcula solo con las vistas de YouTube; aquí el editor tiene el
// veto: excluir una canción (p. ej. no es la oficial) o fijarla en una posición.
export function ChartPanel() {
  const qc = useQueryClient()
  const chart = useQuery({ queryKey: KEY, queryFn: chartApi.obtener })
  const canales = useQuery({ queryKey: KEY_CANALES, queryFn: chartApi.canales })
  const [canalRef, setCanalRef] = useState('')
  const [canalArtista, setCanalArtista] = useState('')
  const [videoRef, setVideoRef] = useState('')
  const [videoArtista, setVideoArtista] = useState('')
  const [busqueda, setBusqueda] = useState('')

  const refrescar = () => qc.invalidateQueries({ queryKey: KEY })

  const recolectar = useMutation({
    mutationFn: chartApi.recolectar,
    onSuccess: (r) => {
      refrescar()
      if (r.error_estadisticas) toast.error(r.error_estadisticas)
      else if (r.canales_con_error.length) toast.warning(`${r.canales_con_error.length} canal(es) con error`)
      else toast.success(`Listo: ${r.videos_seguidos} videos, ${r.videos_nuevos} nuevos.`)
    },
    onError: (e) => toast.error(errorMessage(e)),
  })
  const decidir = useMutation({
    mutationFn: ({ id, cambio }: { id: string; cambio: Parameters<typeof chartApi.decidir>[1] }) =>
      chartApi.decidir(id, cambio),
    onSuccess: refrescar,
    onError: (e) => toast.error(errorMessage(e)),
  })
  const agregarCanal = useMutation({
    mutationFn: () => chartApi.agregarCanal(canalRef.trim(), canalArtista.trim() || null),
    onSuccess: (c) => {
      toast.success(`Siguiendo a ${c.nombre}. Pulsa «Actualizar ahora» para traer sus videos.`)
      setCanalRef('')
      setCanalArtista('')
      qc.invalidateQueries({ queryKey: KEY_CANALES })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })
  const quitarCanal = useMutation({
    mutationFn: (id: string) => chartApi.quitarCanal(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY_CANALES }),
    onError: (e) => toast.error(errorMessage(e)),
  })
  const agregarVideo = useMutation({
    mutationFn: () => chartApi.agregarVideo(videoRef.trim(), videoArtista.trim() || null),
    onSuccess: () => {
      toast.success('Video agregado. Pulsa «Actualizar ahora» para medirlo.')
      setVideoRef('')
      setVideoArtista('')
      refrescar()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const data = chart.data
  const ocupado = decidir.isPending
  const q = normalizar(busqueda.trim())
  const videosFiltrados = (data?.videos ?? []).filter(
    (v) => !q || normalizar(`${v.titulo} ${v.artista ?? ''}`).includes(q),
  )

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Chart Vallenato</h2>
          <p className="text-sm text-muted-foreground">
            Se calcula solo con las vistas ganadas en YouTube los últimos 7 días. Tú puedes excluir
            o fijar canciones.
            {data?.actualizado ? ` Última medición: ${data.actualizado}.` : ''}
          </p>
        </div>
        <Button onClick={() => recolectar.mutate()} disabled={recolectar.isPending}>
          <RefreshCw className={recolectar.isPending ? 'animate-spin' : ''} />
          {recolectar.isPending ? 'Consultando YouTube…' : 'Actualizar ahora'}
        </Button>
      </div>

      {data && !data.youtube_configurado && (
        <p className="rounded-md bg-warning-bg px-3 py-2 text-sm text-warning">
          Falta la clave de YouTube: agrega la variable <code>YOUTUBE_API_KEY</code> en Railway
          (servicio portal-newsroom-ai) para poder medir.
        </p>
      )}

      <EdicionesSection />

      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">Top 10 actual (en vivo, solo para ti)</h3>
        {chart.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : !data || data.filas.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Aún no hay ranking: necesita al menos 3 días de mediciones. Agrega canales abajo y
            actualiza.
          </p>
        ) : (
          <ol className="flex flex-col gap-1">
            {data.filas.map((f) => (
              <li key={f.video_id} className="flex items-center gap-3 rounded-lg border border-border p-2 text-sm">
                <span className="w-6 text-center text-base font-bold text-brand">{f.posicion}</span>
                <Tendencia fila={f} />
                <div className="min-w-0 flex-1">
                  <a className="block truncate font-medium hover:underline" href={f.url} target="_blank" rel="noopener">
                    {f.titulo}
                  </a>
                  <p className="text-xs text-muted-foreground">
                    {f.artista ?? 'Sin artista'} · +{num(f.vistas_semana)} esta semana
                    {f.parcial ? ' (estimado)' : ''}
                  </p>
                </div>
                {f.fijado && <Pin className="size-4 text-brand" aria-label="Fijado" />}
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={ocupado}
                  onClick={() => decidir.mutate({ id: f.video_id, cambio: { excluido: true } })}
                >
                  Excluir
                </Button>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">
          Videos seguidos ({q ? `${videosFiltrados.length} de ` : ''}
          {data?.videos.length ?? 0})
        </h3>
        <Input
          type="search"
          placeholder="Buscar por título o artista…"
          aria-label="Buscar video por título o artista"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
        />
        <ul className="flex max-h-96 flex-col gap-1 overflow-y-auto">
          {videosFiltrados.length === 0 && (
            <li className="text-sm text-muted-foreground">
              {q ? 'Ningún video coincide con esa búsqueda.' : 'Aún no hay videos.'}
            </li>
          )}
          {videosFiltrados.map((v) => (
            <li key={v.video_id} className="flex flex-wrap items-center gap-2 rounded-lg border border-border p-2 text-sm">
              <div className="min-w-0 flex-1">
                <a className="block truncate hover:underline" href={v.url} target="_blank" rel="noopener">
                  {v.titulo}
                </a>
                <p className="text-xs text-muted-foreground">
                  {v.artista ?? 'Sin artista'}
                  {v.manual ? ' · manual' : ''}
                  {v.vistas_semana != null ? ` · +${num(v.vistas_semana)} semana` : ' · sin medir aún'}
                  {v.excluido ? ' · EXCLUIDO' : ''}
                  {v.es_short && v.fijado_posicion == null ? ' · Short/clip (omitido)' : ''}
                  {v.fijado_posicion ? ` · fijado en #${v.fijado_posicion}` : ''}
                </p>
              </div>
              <SelectNative
                aria-label="Fijar en posición"
                className="!h-8 w-24 text-xs"
                value={v.fijado_posicion ?? ''}
                disabled={ocupado}
                onChange={(e) =>
                  e.target.value
                    ? decidir.mutate({ id: v.video_id, cambio: { fijar_en: Number(e.target.value) } })
                    : decidir.mutate({ id: v.video_id, cambio: { quitar_fijo: true } })
                }
              >
                <option value="">Fijar…</option>
                {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>
                    #{n}
                  </option>
                ))}
              </SelectNative>
              <Button
                size="sm"
                variant="secondary"
                disabled={ocupado}
                onClick={() => decidir.mutate({ id: v.video_id, cambio: { excluido: !v.excluido } })}
              >
                {v.excluido ? 'Incluir' : 'Excluir'}
              </Button>
            </li>
          ))}
        </ul>
      </section>

      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">Canales de YouTube que se siguen</h3>
        <p className="text-xs text-muted-foreground">
          Pega la dirección del canal, su @usuario o su ID. Sus videos nuevos entran solos al chart.
        </p>
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (canalRef.trim()) agregarCanal.mutate()
          }}
        >
          <Input className="min-w-56 flex-1" placeholder="@usuario o enlace del canal" value={canalRef} onChange={(e) => setCanalRef(e.target.value)} />
          <Input className="w-48" placeholder="Artista (opcional)" value={canalArtista} onChange={(e) => setCanalArtista(e.target.value)} />
          <Button type="submit" disabled={agregarCanal.isPending || !canalRef.trim()}>
            Seguir canal
          </Button>
        </form>
        <ul className="flex flex-col gap-1">
          {canales.data?.map((c) => (
            <li key={c.canal_id} className="flex items-center justify-between gap-2 rounded-lg border border-border p-2 text-sm">
              <span className="min-w-0 truncate">
                {c.nombre}
                {c.artista ? <span className="text-muted-foreground"> · {c.artista}</span> : null}
              </span>
              <Button size="sm" variant="ghost" aria-label={`Dejar de seguir ${c.nombre}`} onClick={() => quitarCanal.mutate(c.canal_id)}>
                <Trash2 />
              </Button>
            </li>
          ))}
          {canales.data?.length === 0 && <li className="text-sm text-muted-foreground">Aún no sigues ningún canal.</li>}
        </ul>
      </section>

      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">Agregar un video suelto</h3>
        <p className="text-xs text-muted-foreground">
          Para canciones de artistas cuyo canal no sigues: pega el enlace del video.
        </p>
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (videoRef.trim()) agregarVideo.mutate()
          }}
        >
          <Input className="min-w-56 flex-1" placeholder="Enlace del video de YouTube" value={videoRef} onChange={(e) => setVideoRef(e.target.value)} />
          <Input className="w-48" placeholder="Artista (opcional)" value={videoArtista} onChange={(e) => setVideoArtista(e.target.value)} />
          <Button type="submit" disabled={agregarVideo.isPending || !videoRef.trim()}>
            Agregar video
          </Button>
        </form>
      </section>
    </div>
  )
}
