import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ListChecks } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SelectNative } from '@/components/ui/select-native'
import { formatFechaHoraNegocio } from '@/lib/format'
import { solicitudesApi, type CanalPublicacion, type DestinoPublicacion } from './api'
import { CANALES_DESTINO, DESTINO_ESTADO_BADGE, DESTINO_ESTADO_LABELS } from './utils'

// "elegir de posts recientes" (conversación de automatización 2026-08-20):
// en vez de salir de la app a buscar el link publicado, se elige de una
// lista corta de los últimos posts del canal. Hoy trae datos de
// demostración (marcados "[DEMO]" — ver agents/meta_social/fake_reader.py)
// hasta que haya credenciales reales de Meta Graph API.
function PostsRecientesPicker({
  canal,
  onElegir,
}: {
  canal: Exclude<CanalPublicacion, 'wordpress'>
  onElegir: (permalink: string) => void
}) {
  const [open, setOpen] = useState(false)
  const query = useQuery({
    queryKey: ['posts-recientes', canal],
    queryFn: () => solicitudesApi.postsRecientes(canal),
    enabled: open,
  })

  return (
    <div className="relative">
      <Button type="button" size="sm" variant="secondary" onClick={() => setOpen((v) => !v)}>
        <ListChecks /> Elegir de posts recientes
      </Button>
      {open && (
        <div className="absolute top-full left-0 z-10 mt-1 max-h-64 w-72 overflow-y-auto rounded-md border border-border bg-card p-1 shadow-lg">
          {query.isLoading && <p className="p-2 text-xs text-muted-foreground">Cargando…</p>}
          {query.isError && <p className="p-2 text-xs text-danger">{errorMessage(query.error)}</p>}
          {query.data?.length === 0 && (
            <p className="p-2 text-xs text-muted-foreground">Sin posts recientes.</p>
          )}
          {query.data?.map((post) => (
            <button
              key={post.id}
              type="button"
              className="flex w-full flex-col gap-0.5 rounded p-2 text-left text-xs hover:bg-accent"
              onClick={() => {
                onElegir(post.permalink)
                setOpen(false)
              }}
            >
              <span className="text-muted-foreground">{formatFechaHoraNegocio(post.fecha_publicacion)}</span>
              <span className="line-clamp-2">{post.texto}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function DestinoRow({
  solicitudId,
  destino,
  onChanged,
}: {
  solicitudId: string
  destino: DestinoPublicacion
  onChanged: () => void
}) {
  const [url, setUrl] = useState('')
  const [editandoEnlace, setEditandoEnlace] = useState(false)
  const [enlaceCorregido, setEnlaceCorregido] = useState('')
  const canalLabel = CANALES_DESTINO.find((c) => c.value === destino.canal)?.label ?? destino.canal

  const crearBorradorMutation = useMutation({
    mutationFn: () => solicitudesApi.crearBorradorWordpress(solicitudId, destino.id),
    onSuccess: () => {
      toast.success('Borrador creado en WordPress.')
      onChanged()
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const confirmarMutation = useMutation({
    mutationFn: () => solicitudesApi.confirmarDestino(solicitudId, destino.id, url.trim() || null),
    onSuccess: () => {
      toast.success('Destino confirmado.')
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
      solicitudesApi.corregirEnlaceDestino(solicitudId, destino.id, destino.canal, enlaceCorregido.trim()),
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
          onChange={(e) => setEnlaceCorregido(e.target.value)}
        />
        {destino.canal !== 'wordpress' && (
          <PostsRecientesPicker canal={destino.canal} onElegir={setEnlaceCorregido} />
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
            <Button size="sm" disabled={acting} onClick={() => confirmarMutation.mutate()}>
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
          onChange={(e) => setUrl(e.target.value)}
        />
        <PostsRecientesPicker canal={destino.canal} onElegir={setUrl} />
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

export function DestinosPanel({ solicitudId }: { solicitudId: string }) {
  const queryClient = useQueryClient()
  const [canal, setCanal] = useState<CanalPublicacion | ''>('')
  const key = ['destinos', solicitudId]

  const destinosQuery = useQuery({ queryKey: key, queryFn: () => solicitudesApi.listDestinos(solicitudId) })

  function onChanged() {
    queryClient.invalidateQueries({ queryKey: key })
    queryClient.invalidateQueries({ queryKey: ['reporte', solicitudId] })
    // Confirming/cancelling a destino can complete the solicitud (moves
    // it to Publicadas) and consume Pauta quota — same "heavy refresh"
    // the legacy app does after these two actions.
    queryClient.invalidateQueries({ queryKey: ['solicitudes-kanban'] })
    queryClient.invalidateQueries({ queryKey: ['pautas'] })
  }

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
            <DestinoRow key={d.id} solicitudId={solicitudId} destino={d} onChanged={onChanged} />
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
