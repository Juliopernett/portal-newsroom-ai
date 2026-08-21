import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Paperclip, Plus, RefreshCw, Search, X } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { clientsApi } from '@/features/clientes/api'
import { PAUTA_TIPO_LABELS, pautasApi, type Pauta } from '@/features/contratos/api'
import { formatFecha, formatMoneda } from '@/lib/format'
import {
  solicitudesApi,
  type CanalPublicacion,
  type SolicitudCreateInput,
  type SolicitudEditInput,
} from './api'
import { SolicitudCard } from './SolicitudCard'
import { ActividadReciente } from './ActividadReciente'
import { MetricasSolicitudes } from './MetricasSolicitudes'
import { PautaCombobox } from './PautaCombobox'
import { ClienteCombobox } from './ClienteCombobox'
import { CANALES_DESTINO } from './utils'

const KANBAN_KEY = ['solicitudes-kanban']
const PAUTAS_KEY = ['pautas']
const CLIENTS_KEY = ['clients']
const PUBLICADAS_VISIBLES = 30

const EMPTY_FORM = {
  pautaId: '',
  clienteId: '',
  titulo: '',
  texto: '',
  prioridad: false,
  canales: [] as CanalPublicacion[],
}

export function SolicitudesPage() {
  const queryClient = useQueryClient()
  const location = useLocation()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY_FORM)
  const [formAbierto, setFormAbierto] = useState(false)
  const [adjuntoAbierto, setAdjuntoAbierto] = useState(false)
  const [archivo, setArchivo] = useState<File | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [soloSinDestino, setSoloSinDestino] = useState(false)
  const textoRef = useRef<HTMLTextAreaElement>(null)

  const kanbanQuery = useQuery({ queryKey: KANBAN_KEY, queryFn: solicitudesApi.loadKanban })
  const pautasQuery = useQuery({ queryKey: PAUTAS_KEY, queryFn: pautasApi.list })
  const clientsQuery = useQuery({ queryKey: CLIENTS_KEY, queryFn: clientsApi.list })

  const clientesById = useMemo(() => {
    const map = new Map<string, string>()
    for (const c of clientsQuery.data ?? []) map.set(c.id, c.nombre)
    return map
  }, [clientsQuery.data])

  const pautasById = useMemo(() => {
    const map = new Map<string, Pauta>()
    for (const p of pautasQuery.data ?? []) map.set(p.id, p)
    return map
  }, [pautasQuery.data])

  const pautasVigentes = useMemo(
    () => (pautasQuery.data ?? []).filter((p) => p.vigente),
    [pautasQuery.data],
  )

  const pautaSeleccionada = form.pautaId ? (pautasById.get(form.pautaId) ?? null) : null

  // Cross-module deep link (from Clientes' "Registrar publicación") — same
  // navigation-state pattern as Contratos' preselectClientId. Legacy's
  // quickSolicitudParaCliente prefills the client's vigente pauta and
  // focuses the texto field so the operator can paste and submit right away.
  useEffect(() => {
    const state = location.state as { prefillClientId?: string } | null
    if (state?.prefillClientId && pautasQuery.data) {
      const pauta = pautasVigentes.find((p) => p.client_id === state.prefillClientId)
      if (pauta) setForm((f) => ({ ...f, pautaId: pauta.id }))
      setFormAbierto(true)
      // The form (and its textarea) only mounts once formAbierto flips —
      // deferred so this runs after that render commits, not before.
      setTimeout(() => textoRef.current?.focus(), 0)
      navigate(location.pathname, { replace: true, state: null })
    }
  }, [location.state, location.pathname, navigate, pautasQuery.data, pautasVigentes])

  function invalidateKanban() {
    queryClient.invalidateQueries({ queryKey: KANBAN_KEY })
  }

  const createMutation = useMutation({
    mutationFn: async ({ payload, archivo }: { payload: SolicitudCreateInput; archivo: File | null }) => {
      const solicitud = await solicitudesApi.create(payload)
      if (archivo) {
        // Best-effort: the solicitud itself must exist first (media is
        // scoped to a publication_request_id), so this is a second call
        // right after creation — if it fails, the solicitud still got
        // created; the operator can attach the file later from its card.
        try {
          await solicitudesApi.uploadMedia(solicitud.id, archivo)
        } catch (err) {
          toast.error(`Solicitud registrada, pero el archivo no se pudo subir: ${errorMessage(err)}`)
          return solicitud
        }
      }
      return solicitud
    },
    onSuccess: () => {
      invalidateKanban()
      setForm(EMPTY_FORM)
      setArchivo(null)
      setAdjuntoAbierto(false)
      toast.success('Solicitud registrada.')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const publishMutation = useMutation({
    mutationFn: solicitudesApi.publish,
    onSuccess: () => {
      invalidateKanban()
      queryClient.invalidateQueries({ queryKey: PAUTAS_KEY })
      toast.success('Solicitud publicada.')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const cancelMutation = useMutation({
    mutationFn: solicitudesApi.cancelar,
    onSuccess: () => {
      invalidateKanban()
      toast.success('Solicitud cancelada.')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const linkMutation = useMutation({
    mutationFn: ({ id, pautaId }: { id: string; pautaId: string }) =>
      solicitudesApi.linkPauta(id, pautaId),
    onSuccess: () => {
      invalidateKanban()
      // Linking a pauta to a solicitud that's already completa consumes
      // cupo immediately (publicaciones_consumidas is derived live from
      // pauta_id + esta_completa) — invalidate pautas too so cupo badges
      // refresh right away instead of only after the next unrelated fetch.
      queryClient.invalidateQueries({ queryKey: PAUTAS_KEY })
      toast.success('Pauta vinculada.')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const editMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: SolicitudEditInput }) =>
      solicitudesApi.edit(id, payload),
    onSuccess: () => {
      invalidateKanban()
      toast.success('Solicitud actualizada.')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const isActing =
    publishMutation.isPending || cancelMutation.isPending || linkMutation.isPending || editMutation.isPending

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const payload: SolicitudCreateInput = {
      pauta_id: form.pautaId || null,
      client_id: form.pautaId ? null : form.clienteId || null,
      titulo: form.titulo.trim() || null,
      texto: form.texto,
      prioridad_manual: form.prioridad,
      canales: form.canales,
    }
    createMutation.mutate({ payload, archivo })
  }

  function toggleCanal(canal: CanalPublicacion) {
    setForm((f) => ({
      ...f,
      canales: f.canales.includes(canal)
        ? f.canales.filter((c) => c !== canal)
        : [...f.canales, canal],
    }))
  }

  function handleTextoKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      ;(e.currentTarget.form as HTMLFormElement)?.requestSubmit()
    }
  }

  const pendientes = kanbanQuery.data?.pendientes ?? []
  const publicadasTodas = kanbanQuery.data?.publicadas ?? []
  const publicadasVisibles = publicadasTodas.slice(0, PUBLICADAS_VISIBLES)

  // "Publicaciones sin destino" (filtro rápido, 2026-08-20): acotado a
  // contratos activos a propósito — repasar los ~1000+ registros
  // históricos no tiene sentido operativo, solo lo que aún se puede
  // corregir. Una sola llamada al backend — antes esto pedía un
  // GET .../destinos por solicitud candidata (hasta ~180 en paralelo),
  // suficiente para saturar la conexión un momento.
  const sinDestinoQuery = useQuery({
    queryKey: ['solicitudes-sin-destino-social'],
    queryFn: solicitudesApi.sinDestinoSocial,
    enabled: soloSinDestino,
  })
  const idsSinDestino = useMemo(
    () => new Set((sinDestinoQuery.data ?? []).map((s) => s.id)),
    [sinDestinoQuery.data],
  )

  // pauta_id wins when both are present (it's the authoritative link once a
  // contrato is known); client_id is the fallback identity captured at
  // intake, so a request that hasn't been linked to a Pauta yet still has
  // an owner instead of showing as anonymous in the queue.
  function clienteIdDe(s: { pauta_id: string | null; client_id: string | null }) {
    if (s.pauta_id) return pautasById.get(s.pauta_id)?.client_id ?? null
    return s.client_id
  }

  function clienteDe(s: { pauta_id: string | null; client_id: string | null }) {
    const clienteId = clienteIdDe(s)
    return clienteId ? (clientesById.get(clienteId) ?? '(sin vincular)') : '(sin vincular)'
  }

  const busquedaTrim = busqueda.trim().toLowerCase()
  function coincide(s: { texto: string; titulo: string | null; pauta_id: string | null; client_id: string | null }) {
    if (!busquedaTrim) return true
    return (
      clienteDe(s).toLowerCase().includes(busquedaTrim) ||
      s.texto.toLowerCase().includes(busquedaTrim) ||
      (s.titulo ?? '').toLowerCase().includes(busquedaTrim)
    )
  }
  const pendientesVisibles = pendientes.filter(coincide)
  // A search query (or the "sin destino" filter) must reach every
  // publicada ever loaded, not just the 30 most recent — otherwise older
  // matches silently vanish despite the full list already sitting in
  // memory. With neither active, keep the cheap 30-item cap.
  const publicadasFiltradas = (busquedaTrim || soloSinDestino ? publicadasTodas : publicadasVisibles)
    .filter(coincide)
    .filter((s) => !soloSinDestino || idsSinDestino.has(s.id))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">Solicitudes</h1>
          <p className="text-sm text-muted-foreground">Cola de publicaciones del día</p>
        </div>
        <Button
          variant="outline"
          size="icon"
          aria-label="Actualizar"
          onClick={() => {
            kanbanQuery.refetch()
            pautasQuery.refetch()
          }}
        >
          <RefreshCw className={kanbanQuery.isFetching ? 'animate-spin' : ''} />
        </Button>
      </div>

      {!kanbanQuery.isLoading && (
        <MetricasSolicitudes
          pendientes={pendientes}
          publicadas={publicadasTodas}
          pautasById={pautasById}
          pautas={pautasQuery.data ?? []}
        />
      )}

      {!formAbierto ? (
        <Button className="self-start" onClick={() => setFormAbierto(true)}>
          <Plus /> Nueva solicitud
        </Button>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-2 rounded-lg border border-border p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-muted-foreground">Nueva solicitud</span>
            <button
              type="button"
              aria-label="Cerrar"
              className="text-muted-foreground hover:text-foreground"
              onClick={() => setFormAbierto(false)}
            >
              <X className="size-4" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            <PautaCombobox
              pautas={pautasVigentes}
              clientesById={clientesById}
              value={form.pautaId}
              onChange={(pautaId) => setForm({ ...form, pautaId, clienteId: pautaId ? '' : form.clienteId })}
            />
            {!form.pautaId && (
              <ClienteCombobox
                clients={clientsQuery.data ?? []}
                value={form.clienteId}
                onChange={(clienteId) => setForm({ ...form, clienteId })}
              />
            )}
            <Input
              className="min-w-[16rem] flex-1"
              placeholder="Título (opcional)"
              value={form.titulo}
              onChange={(e) => setForm({ ...form, titulo: e.target.value })}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.prioridad}
                onChange={(e) => setForm({ ...form, prioridad: e.target.checked })}
              />
              Prioridad
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs text-muted-foreground">Destinos:</span>
            {CANALES_DESTINO.map((c) => (
              <label key={c.value} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={form.canales.includes(c.value)}
                  onChange={() => toggleCanal(c.value)}
                />
                {c.label}
              </label>
            ))}
          </div>

          {pautaSeleccionada && (
            <div className="flex flex-wrap items-center gap-3 rounded-md bg-muted p-2 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">
                {clientesById.get(pautaSeleccionada.client_id) ?? '(cliente desconocido)'}
              </span>
              <span>{PAUTA_TIPO_LABELS[pautaSeleccionada.tipo]}</span>
              <span>
                {formatFecha(pautaSeleccionada.fecha_inicio)} – {formatFecha(pautaSeleccionada.fecha_fin)}
              </span>
              <span>
                {pautaSeleccionada.publicaciones_restantes}/{pautaSeleccionada.publicaciones_contratadas} restantes
              </span>
              <span>{formatMoneda(pautaSeleccionada.valor_pagado)}</span>
            </div>
          )}

          <Textarea
            ref={textoRef}
            required
            rows={2}
            placeholder="Pegar texto de la publicación… (Ctrl/Cmd+Enter para enviar)"
            value={form.texto}
            onChange={(e) => setForm({ ...form, texto: e.target.value })}
            onKeyDown={handleTextoKeyDown}
          />

          {!adjuntoAbierto ? (
            <button
              type="button"
              className="flex items-center gap-1.5 self-start text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setAdjuntoAbierto(true)}
            >
              <Paperclip className="size-3.5" /> Adjuntar material (opcional)
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <Paperclip className="size-4 shrink-0 text-muted-foreground" />
              <input
                type="file"
                accept="image/*,video/*"
                className="text-base sm:text-xs"
                onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
              />
              <button
                type="button"
                className="text-muted-foreground hover:text-foreground"
                aria-label="Quitar adjunto"
                onClick={() => {
                  setArchivo(null)
                  setAdjuntoAbierto(false)
                }}
              >
                <X className="size-3.5" />
              </button>
            </div>
          )}

          <Button type="submit" disabled={createMutation.isPending} className="self-start">
            <Plus /> {createMutation.isPending ? 'Registrando…' : 'Registrar'}
          </Button>
        </form>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative max-w-sm flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por cliente o texto…"
            className="pl-9"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </div>
        <Button
          type="button"
          variant={soloSinDestino ? 'default' : 'secondary'}
          size="sm"
          onClick={() => setSoloSinDestino((v) => !v)}
          title="Publicadas de contratos activos sin Facebook ni Instagram registrado"
        >
          Sin destino (contratos activos)
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_16rem_1fr]">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-sm font-medium">
            Cola de trabajo
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {pendientes.length}
            </span>
          </div>
          <div className="flex flex-col gap-2">
            {kanbanQuery.isLoading ? (
              <p className="p-6 text-center text-sm text-muted-foreground">Cargando…</p>
            ) : pendientes.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">No hay solicitudes pendientes.</p>
            ) : pendientesVisibles.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">Nada coincide con "{busqueda}".</p>
            ) : (
              pendientesVisibles.map((s) => (
                <SolicitudCard
                  key={s.id}
                  solicitud={s}
                  esPublicada={false}
                  pauta={s.pauta_id ? (pautasById.get(s.pauta_id) ?? null) : null}
                  clienteNombre={clienteDe(s)}
                  clienteId={clienteIdDe(s)}
                  pautasVigentes={pautasVigentes}
                  clientesById={clientesById}
                  isActing={isActing}
                  onPublicar={(id) => publishMutation.mutate(id)}
                  onCancelar={(id) => cancelMutation.mutate(id)}
                  onVincular={(id, pautaId) => {
                    if (!pautaId) {
                      toast.error('Elige una pauta antes de vincular.')
                      return
                    }
                    linkMutation.mutate({ id, pautaId })
                  }}
                  onGuardarEdicion={(id, payload) => editMutation.mutate({ id, payload })}
                  onVerCliente={(id) => navigate('/clientes', { state: { abrirFichaClientId: id } })}
                />
              ))
            )}
          </div>
        </div>

        <ActividadReciente
          pendientes={pendientes}
          publicadas={publicadasTodas}
          pautas={pautasQuery.data ?? []}
          clientesById={clientesById}
        />

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-sm font-medium">
            Publicadas
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {publicadasTodas.length}
            </span>
          </div>
          <div className="flex flex-col gap-2">
            {kanbanQuery.isLoading ? (
              <p className="p-6 text-center text-sm text-muted-foreground">Cargando…</p>
            ) : publicadasVisibles.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">Todavía no hay publicadas.</p>
            ) : soloSinDestino && sinDestinoQuery.isFetching ? (
              <p className="p-6 text-center text-sm text-muted-foreground">Revisando destinos…</p>
            ) : publicadasFiltradas.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">
                {soloSinDestino
                  ? busquedaTrim
                    ? `Nada coincide con "${busqueda}".`
                    : 'Ninguna publicación de un contrato activo está sin Facebook/Instagram.'
                  : `Nada coincide con "${busqueda}".`}
              </p>
            ) : (
              publicadasFiltradas.map((s) => (
                <SolicitudCard
                  key={s.id}
                  solicitud={s}
                  esPublicada
                  pauta={s.pauta_id ? (pautasById.get(s.pauta_id) ?? null) : null}
                  clienteNombre={clienteDe(s)}
                  clienteId={clienteIdDe(s)}
                  pautasVigentes={pautasVigentes}
                  clientesById={clientesById}
                  isActing={isActing}
                  onPublicar={() => {}}
                  onCancelar={() => {}}
                  onVincular={(id, pautaId) => {
                    if (!pautaId) {
                      toast.error('Elige una pauta antes de vincular.')
                      return
                    }
                    linkMutation.mutate({ id, pautaId })
                  }}
                  onGuardarEdicion={() => {}}
                  onVerCliente={(id) => navigate('/clientes', { state: { abrirFichaClientId: id } })}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
