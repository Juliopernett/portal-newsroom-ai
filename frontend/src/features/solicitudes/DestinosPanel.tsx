import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ListChecks } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SelectNative } from '@/components/ui/select-native'
import { formatFechaHoraNegocio } from '@/lib/format'
import {
  solicitudesApi,
  type CanalPublicacion,
  type DestinoPublicacion,
  type PostRedSocial,
  type SolicitudContexto,
} from './api'
import { CANALES_DESTINO, DESTINO_ESTADO_BADGE, DESTINO_ESTADO_LABELS } from './utils'

// Umbral a partir del cual vale la pena destacar una coincidencia — por
// debajo de esto el puntaje es ruido, no una sugerencia real (conversación
// de conciliación inteligente, 2026-08-20).
const UMBRAL_COINCIDENCIA_DESTACADA = 0.3

// "elegir de posts recientes" — en vez de salir de la app a buscar el link
// publicado, se elige de una lista corta de los últimos posts del canal.
// Con contexto de la solicitud (título/texto/cliente/fecha), el backend
// calcula una coincidencia sugerida y ordena los candidatos por ella —
// pero la relación SIEMPRE requiere el clic explícito en "Relacionar";
// nunca se relaciona nada automáticamente, sin importar el puntaje.
function PostsRecientesPicker({
  canal,
  contexto,
  onElegir,
}: {
  canal: Exclude<CanalPublicacion, 'wordpress'>
  contexto?: SolicitudContexto
  onElegir: (post: PostRedSocial) => void
}) {
  const [open, setOpen] = useState(false)
  const query = useQuery({
    queryKey: ['posts-recientes', canal, contexto],
    queryFn: () => solicitudesApi.postsRecientes(canal, contexto),
    enabled: open,
  })

  return (
    <div className="relative">
      <Button type="button" size="sm" variant="secondary" onClick={() => setOpen((v) => !v)}>
        <ListChecks /> Elegir de posts recientes
      </Button>
      {open && (
        <div className="absolute top-full left-0 z-10 mt-1 max-h-96 w-96 overflow-y-auto rounded-md border border-border bg-card p-1 shadow-lg">
          {query.isLoading && <p className="p-2 text-xs text-muted-foreground">Cargando…</p>}
          {query.isError && <p className="p-2 text-xs text-danger">{errorMessage(query.error)}</p>}
          {query.data?.length === 0 && (
            <p className="p-2 text-xs text-muted-foreground">Sin posts recientes.</p>
          )}
          {query.data?.map((post) => (
            <div
              key={post.id}
              className="flex gap-2 rounded p-2 text-xs hover:bg-accent"
            >
              {post.miniatura_url && (
                <img
                  src={post.miniatura_url}
                  alt=""
                  className="size-14 shrink-0 rounded object-cover"
                />
              )}
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <div className="flex flex-wrap items-center gap-1">
                  {post.coincidencia !== null && post.coincidencia >= UMBRAL_COINCIDENCIA_DESTACADA && (
                    <span className="rounded-full bg-brand/10 px-1.5 py-0.5 text-[10px] font-medium text-brand">
                      ✨ {Math.round(post.coincidencia * 100)}% de coincidencia
                    </span>
                  )}
                  {post.ya_relacionada && (
                    <span className="rounded-full bg-success-bg px-1.5 py-0.5 text-[10px] font-medium text-success">
                      ✓ Ya relacionada
                    </span>
                  )}
                </div>
                <span className="line-clamp-2 text-foreground">{post.texto}</span>
                <span className="text-muted-foreground">
                  📅 {formatFechaHoraNegocio(post.fecha_publicacion)}
                </span>
                <div className="flex items-center gap-2">
                  <a
                    href={post.permalink}
                    target="_blank"
                    rel="noopener"
                    className="text-brand underline"
                  >
                    Ver publicación
                  </a>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    className="h-6 px-2 text-[10px]"
                    onClick={() => {
                      onElegir(post)
                      setOpen(false)
                    }}
                  >
                    Relacionar
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function DestinoRow({
  solicitudId,
  destino,
  contexto,
  onChanged,
}: {
  solicitudId: string
  destino: DestinoPublicacion
  contexto?: SolicitudContexto
  onChanged: () => void
}) {
  const [url, setUrl] = useState('')
  const [metaPostId, setMetaPostId] = useState<string | null>(null)
  const [editandoEnlace, setEditandoEnlace] = useState(false)
  const [enlaceCorregido, setEnlaceCorregido] = useState('')
  const [metaPostIdCorregido, setMetaPostIdCorregido] = useState<string | null>(null)
  const canalLabel = CANALES_DESTINO.find((c) => c.value === destino.canal)?.label ?? destino.canal

  const crearBorradorMutation = useMutation({
    mutationFn: () => solicitudesApi.crearBorradorWordpress(solicitudId, destino.id),
    onSuccess: (data) => {
      // La IA prepara el texto antes de crear el borrador (2026-08-21) —
      // si no estuvo disponible, el borrador igual se crea con el texto
      // original, así que el toast lo dice en vez de aparentar que todo
      // salió con preparación editorial.
      toast.success(
        data.preparacion_ia_estado === 'procesado'
          ? 'Borrador creado en WordPress con preparación editorial IA.'
          : 'Borrador creado en WordPress con el texto original — la preparación con IA no estuvo disponible.',
      )
      onChanged()
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const confirmarMutation = useMutation({
    mutationFn: () =>
      solicitudesApi.confirmarDestino(solicitudId, destino.id, url.trim() || null, metaPostId),
    onSuccess: () => {
      toast.success('Destino confirmado.')
      onChanged()
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  // Sincronización con WordPress (2026-08-24): lo que el botón "Confirmar
  // publicado" de la fila de WordPress dispara ahora — una verificación
  // real contra el post, no una confirmación a ciegas.
  const sincronizarMutation = useMutation({
    mutationFn: () => solicitudesApi.sincronizarWordpress(solicitudId, destino.id),
    onSuccess: (actualizado) => {
      if (actualizado.estado === 'publicado') {
        toast.success('Publicación confirmada — WordPress ya lo tiene publicado.')
      } else if (actualizado.estado === 'fallido') {
        toast.error(actualizado.ultimo_error ?? 'No se pudo sincronizar con WordPress.')
      } else {
        toast('Todavía sigue en borrador en WordPress.')
      }
      onChanged()
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const cancelarMutation = useMutation({
    mutationFn: () => solicitudesApi.cancelarDestino(solicitudId, destino.id),
    onSuccess: () => {
      toast.success('Destino cancelado.')
      onChanged()
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const corregirEnlaceMutation = useMutation({
    mutationFn: () =>
      solicitudesApi.corregirEnlaceDestino(
        solicitudId,
        destino.id,
        destino.canal,
        enlaceCorregido.trim(),
        metaPostIdCorregido,
      ),
    onSuccess: () => {
      toast.success('Enlace corregido.')
      setEditandoEnlace(false)
      onChanged()
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const acting =
    crearBorradorMutation.isPending ||
    confirmarMutation.isPending ||
    sincronizarMutation.isPending ||
    cancelarMutation.isPending ||
    corregirEnlaceMutation.isPending

  let acciones: React.ReactNode = null
  if (destino.estado === 'publicado') {
    const link = destino.canal === 'wordpress' ? destino.wp_url : destino.url_publicacion
    acciones = editandoEnlace ? (
      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="h-8 w-48 text-base sm:text-xs"
          placeholder="Enlace correcto"
          value={enlaceCorregido}
          onChange={(e) => {
            setEnlaceCorregido(e.target.value)
            setMetaPostIdCorregido(null)
          }}
        />
        {destino.canal !== 'wordpress' && (
          <PostsRecientesPicker
            canal={destino.canal}
            contexto={contexto}
            onElegir={(post) => {
              setEnlaceCorregido(post.permalink)
              setMetaPostIdCorregido(post.id)
            }}
          />
        )}
        <Button
          size="sm"
          disabled={acting || !enlaceCorregido.trim()}
          onClick={() => corregirEnlaceMutation.mutate()}
        >
          Guardar
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={acting}
          onClick={() => setEditandoEnlace(false)}
        >
          Cancelar
        </Button>
      </div>
    ) : (
      <div className="flex flex-wrap items-center gap-2">
        {link && (
          <a className="text-xs text-brand underline" href={link} target="_blank" rel="noopener">
            Ver publicación
          </a>
        )}
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            setEnlaceCorregido(link ?? '')
            setMetaPostIdCorregido(destino.meta_post_id)
            setEditandoEnlace(true)
          }}
        >
          Editar enlace
        </Button>
      </div>
    )
  } else if (destino.canal === 'wordpress') {
    acciones = (
      <div className="flex flex-wrap items-center gap-2">
        {destino.wp_url ? (
          <>
            <a className="text-xs text-brand underline" href={destino.wp_url} target="_blank" rel="noopener">
              Ver borrador
            </a>
            <Button size="sm" disabled={acting} onClick={() => sincronizarMutation.mutate()}>
              Confirmar publicado
            </Button>
          </>
        ) : (
          <Button size="sm" variant="secondary" disabled={acting} onClick={() => crearBorradorMutation.mutate()}>
            Crear borrador
          </Button>
        )}
        {destino.estado !== 'cancelado' && (
          <Button size="sm" variant="secondary" disabled={acting} onClick={() => cancelarMutation.mutate()}>
            Cancelar
          </Button>
        )}
      </div>
    )
  } else {
    acciones = (
      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="h-8 w-48 text-base sm:text-xs"
          placeholder="Enlace de la publicación"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value)
            setMetaPostId(null)
          }}
        />
        <PostsRecientesPicker
          canal={destino.canal}
          contexto={contexto}
          onElegir={(post) => {
            setUrl(post.permalink)
            setMetaPostId(post.id)
          }}
        />
        <Button size="sm" disabled={acting} onClick={() => confirmarMutation.mutate()}>
          Confirmar
        </Button>
        <Button size="sm" variant="secondary" disabled={acting} onClick={() => cancelarMutation.mutate()}>
          Cancelar
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border py-2 text-sm first:border-t-0">
      <div className="flex items-center gap-2">
        <span className="font-medium">{canalLabel}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs ${DESTINO_ESTADO_BADGE[destino.estado]}`}>
          {DESTINO_ESTADO_LABELS[destino.estado]}
        </span>
      </div>
      {acciones}
    </div>
  )
}

export function DestinosPanel({
  solicitudId,
  contexto,
}: {
  solicitudId: string
  contexto?: SolicitudContexto
}) {
  const queryClient = useQueryClient()
  const [canal, setCanal] = useState<CanalPublicacion | ''>('')
  const key = ['destinos', solicitudId]

  const destinosQuery = useQuery({ queryKey: key, queryFn: () => solicitudesApi.listDestinos(solicitudId) })

  const onChanged = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['destinos', solicitudId] })
    queryClient.invalidateQueries({ queryKey: ['reporte', solicitudId] })
    // Confirming/cancelling a destino can complete the solicitud (moves
    // it to Publicadas) and consume Pauta quota — same "heavy refresh"
    // the legacy app does after these two actions. The silent WordPress
    // auto-sync below reuses this too, for the same reason.
    queryClient.invalidateQueries({ queryKey: ['solicitudes-kanban'] })
    queryClient.invalidateQueries({ queryKey: ['pautas'] })
  }, [queryClient, solicitudId])

  const addMutation = useMutation({
    mutationFn: (c: CanalPublicacion) => solicitudesApi.addDestino(solicitudId, c),
    onSuccess: () => {
      toast.success('Destino agregado.')
      setCanal('')
      queryClient.invalidateQueries({ queryKey: key })
      queryClient.invalidateQueries({ queryKey: ['reporte', solicitudId] })
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  // Auto-sync silencioso con WordPress al abrir la solicitud (2026-08-24):
  // el operador ya viene a revisarla, así que aprovechamos esa visita para
  // detectar solo si publicó directamente en WordPress, sin pedirle un
  // clic aparte. Una vez por solicitudId (el ref evita repetirlo en cada
  // refetch que dispara otra mutación) y solo para destinos de WordPress
  // con wp_post_id y todavía no terminales — el resto es no-op en el
  // backend de todas formas, pero evitar la llamada de una vez es más
  // barato. Promise.allSettled: que un post falle no debe frenar a los
  // demás; nada de esto muestra un toast, es la fila la que se repinta
  // sola si algo cambió.
  const sincronizadoParaRef = useRef<string | null>(null)
  useEffect(() => {
    if (!destinosQuery.data || sincronizadoParaRef.current === solicitudId) return
    sincronizadoParaRef.current = solicitudId
    const aSincronizar = destinosQuery.data.filter(
      (d) => d.canal === 'wordpress' && d.wp_post_id && (d.estado === 'pendiente' || d.estado === 'fallido'),
    )
    if (aSincronizar.length === 0) return
    Promise.allSettled(
      aSincronizar.map((d) => solicitudesApi.sincronizarWordpress(solicitudId, d.id)),
    ).then(onChanged)
  }, [destinosQuery.data, solicitudId, onChanged])

  const destinos = destinosQuery.data ?? []
  // Un destino cancelado nunca vuelve a publicarse (marcar_publicado lo
  // rechaza por ser un estado terminal) — así que su canal no debe seguir
  // bloqueando "Agregar destino"; si no, cancelar por error deja ese canal
  // inalcanzable para siempre en esta solicitud.
  const usados = new Set(destinos.filter((d) => d.estado !== 'cancelado').map((d) => d.canal))
  const disponibles = CANALES_DESTINO.filter((c) => !usados.has(c.value))

  return (
    <div className="rounded-md border border-border bg-background p-3">
      {destinosQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : destinos.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin destinos todavía.</p>
      ) : (
        <div className="flex flex-col">
          {destinos.map((d) => (
            <DestinoRow
              key={d.id}
              solicitudId={solicitudId}
              destino={d}
              contexto={contexto}
              onChanged={onChanged}
            />
          ))}
        </div>
      )}

      {disponibles.length > 0 && (
        <div className="mt-2 flex items-center gap-2 border-t border-border pt-2">
          <SelectNative className="h-8 text-base sm:text-xs" value={canal} onChange={(e) => setCanal(e.target.value as CanalPublicacion)}>
            <option value="">Agregar destino…</option>
            {disponibles.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </SelectNative>
          <Button
            size="sm"
            variant="secondary"
            disabled={addMutation.isPending}
            onClick={() => {
              if (!canal) {
                toast.error('Elige un canal antes de agregar.')
                return
              }
              addMutation.mutate(canal)
            }}
          >
            Agregar
          </Button>
        </div>
      )}
    </div>
  )
}
