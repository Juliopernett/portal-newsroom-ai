import { useMemo, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SelectNative } from '@/components/ui/select-native'
import { Textarea } from '@/components/ui/textarea'
import { clientsApi } from '@/features/clientes/api'
import { pautasApi, type Pauta } from '@/features/contratos/api'
import { solicitudesApi, type SolicitudCreateInput, type SolicitudEditInput } from './api'
import { SolicitudCard } from './SolicitudCard'
import { pautaOptionLabel } from './utils'

const KANBAN_KEY = ['solicitudes-kanban']
const PAUTAS_KEY = ['pautas']
const CLIENTS_KEY = ['clients']

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

  function invalidateKanban() {
    queryClient.invalidateQueries({ queryKey: KANBAN_KEY })
  }

  const createMutation = useMutation({
    mutationFn: solicitudesApi.create,
    onSuccess: () => {
      invalidateKanban()
      setForm(EMPTY_FORM)
    },
  })

  const publishMutation = useMutation({
    mutationFn: solicitudesApi.publish,
    onSuccess: () => {
      invalidateKanban()
      queryClient.invalidateQueries({ queryKey: PAUTAS_KEY })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: solicitudesApi.cancelar,
    onSuccess: invalidateKanban,
  })

  const linkMutation = useMutation({
    mutationFn: ({ id, pautaId }: { id: string; pautaId: string }) =>
      solicitudesApi.linkPauta(id, pautaId),
    onSuccess: invalidateKanban,
  })

  const editMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: SolicitudEditInput }) =>
      solicitudesApi.edit(id, payload),
    onSuccess: invalidateKanban,
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
  const publicadas = kanbanQuery.data?.publicadas ?? []

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

      <form onSubmit={handleSubmit} className="flex flex-col gap-2 rounded-lg border border-border p-3">
        <div className="flex flex-wrap gap-2">
          <SelectNative
            className="w-auto max-w-[16rem]"
            value={form.pautaId}
            onChange={(e) => setForm({ ...form, pautaId: e.target.value })}
          >
            <option value="">(sin pauta todavía — se vincula después)</option>
            {pautasVigentes.map((p) => (
              <option key={p.id} value={p.id}>
                {pautaOptionLabel(p, clientesById.get(p.client_id) ?? '(cliente desconocido)')}
              </option>
            ))}
          </SelectNative>
          <Input
            className="w-48"
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
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
                  clienteNombre={
                    s.pauta_id
                      ? (clientesById.get(pautasById.get(s.pauta_id)?.client_id ?? '') ?? '(sin vincular)')
                      : '(sin vincular)'
                  }
                  pautasVigentes={pautasVigentes}
                  clientesById={clientesById}
                  isActing={isActing}
                  onPublicar={(id) => publishMutation.mutate(id)}
                  onCancelar={(id) => cancelMutation.mutate(id)}
                  onVincular={(id, pautaId) => {
                    if (!pautaId) return
                    linkMutation.mutate({ id, pautaId })
                  }}
                  onGuardarEdicion={(id, payload) => editMutation.mutate({ id, payload })}
                />
              ))
            )}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-sm font-medium">
            Publicadas
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {publicadas.length}
            </span>
          </div>
          <div className="flex flex-col gap-2">
            {kanbanQuery.isLoading ? (
              <p className="p-6 text-center text-sm text-muted-foreground">Cargando…</p>
            ) : publicadas.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">Todavía no hay publicadas.</p>
            ) : (
              publicadas.map((s) => (
                <SolicitudCard
                  key={s.id}
                  solicitud={s}
                  esPublicada
                  pauta={s.pauta_id ? (pautasById.get(s.pauta_id) ?? null) : null}
                  clienteNombre={
                    s.pauta_id
                      ? (clientesById.get(pautasById.get(s.pauta_id)?.client_id ?? '') ?? '(sin vincular)')
                      : '(sin vincular)'
                  }
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
