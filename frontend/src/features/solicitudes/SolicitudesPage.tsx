import { useMemo, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { clientsApi } from '@/features/clientes/api'
import { PAUTA_TIPO_LABELS, pautasApi, type Pauta } from '@/features/contratos/api'
import { formatFecha, formatMoneda } from '@/lib/format'
import { solicitudesApi, type SolicitudCreateInput, type SolicitudEditInput } from './api'
import { SolicitudCard } from './SolicitudCard'
import { ActividadReciente } from './ActividadReciente'
import { MetricasSolicitudes } from './MetricasSolicitudes'
import { PautaCombobox } from './PautaCombobox'

const KANBAN_KEY = ['solicitudes-kanban']
const PAUTAS_KEY = ['pautas']
const CLIENTS_KEY = ['clients']
const PUBLICADAS_VISIBLES = 30

const EMPTY_FORM = { pautaId: '', titulo: '', texto: '', prioridad: false }

export function SolicitudesPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(EMPTY_FORM)

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

  function invalidateKanban() {
    queryClient.invalidateQueries({ queryKey: KANBAN_KEY })
  }

  const createMutation = useMutation({
    mutationFn: solicitudesApi.create,
    onSuccess: () => {
      invalidateKanban()
      setForm(EMPTY_FORM)
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
      toast.success('Pauta vinculada. Ya se puede publicar.')
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
      titulo: form.titulo.trim() || null,
      texto: form.texto,
      prioridad_manual: form.prioridad,
    }
    createMutation.mutate(payload)
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

  function clienteDe(s: { pauta_id: string | null }) {
    if (!s.pauta_id) return '(sin vincular)'
    const pauta = pautasById.get(s.pauta_id)
    return pauta ? (clientesById.get(pauta.client_id) ?? '(sin vincular)') : '(sin vincular)'
  }

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

      <form onSubmit={handleSubmit} className="flex flex-col gap-2 rounded-lg border border-border p-3">
        <div className="flex flex-wrap gap-2">
          <PautaCombobox
            pautas={pautasVigentes}
            clientesById={clientesById}
            value={form.pautaId}
            onChange={(pautaId) => setForm({ ...form, pautaId })}
          />
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
          required
          rows={2}
          placeholder="Pegar texto de la publicación… (Ctrl/Cmd+Enter para enviar)"
          value={form.texto}
          onChange={(e) => setForm({ ...form, texto: e.target.value })}
          onKeyDown={handleTextoKeyDown}
        />
        <Button type="submit" disabled={createMutation.isPending} className="self-start">
          <Plus /> Registrar
        </Button>
      </form>

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
            ) : (
              pendientes.map((s) => (
                <SolicitudCard
                  key={s.id}
                  solicitud={s}
                  esPublicada={false}
                  pauta={s.pauta_id ? (pautasById.get(s.pauta_id) ?? null) : null}
                  clienteNombre={clienteDe(s)}
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
            ) : (
              publicadasVisibles.map((s) => (
                <SolicitudCard
                  key={s.id}
                  solicitud={s}
                  esPublicada
                  pauta={s.pauta_id ? (pautasById.get(s.pauta_id) ?? null) : null}
                  clienteNombre={clienteDe(s)}
                  pautasVigentes={pautasVigentes}
                  clientesById={clientesById}
                  isActing={isActing}
                  onPublicar={() => {}}
                  onCancelar={() => {}}
                  onVincular={() => {}}
                  onGuardarEdicion={() => {}}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
