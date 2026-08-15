import { useState } from 'react'
import { Check, Link2, Pencil, Flag, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { SelectNative } from '@/components/ui/select-native'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import type { Pauta } from '@/features/contratos/api'
import { formatFechaHoraNegocio, formatMoneda } from '@/lib/format'
import { PAUTA_TIPO_LABELS } from '@/features/contratos/api'
import type { Solicitud, SolicitudEditInput } from './api'
import { esperandoMucho, formatHoras, horasEnEspera, motivoPrioridadCorto, pautaOptionLabel, scoreSolicitud } from './utils'

export function SolicitudCard({
  solicitud,
  esPublicada,
  pauta,
  clienteNombre,
  pautasVigentes,
  clientesById,
  onPublicar,
  onCancelar,
  onVincular,
  onGuardarEdicion,
  isActing,
}: {
  solicitud: Solicitud
  esPublicada: boolean
  pauta: Pauta | null
  clienteNombre: string
  pautasVigentes: Pauta[]
  clientesById: Map<string, string>
  onPublicar: (id: string) => void
  onCancelar: (id: string) => void
  onVincular: (id: string, pautaId: string) => void
  onGuardarEdicion: (id: string, payload: SolicitudEditInput) => void
  isActing: boolean
}) {
  const [editing, setEditing] = useState(false)
  const [selectedPautaId, setSelectedPautaId] = useState('')
  const [editTitulo, setEditTitulo] = useState(solicitud.titulo ?? '')
  const [editTexto, setEditTexto] = useState(solicitud.texto)
  const [editPrioridad, setEditPrioridad] = useState(solicitud.prioridad_manual)

  const esRecibida = !esPublicada && solicitud.estado === 'recibida'
  const esEnCurso = !esPublicada && solicitud.estado === 'aceptada'
  const horas = horasEnEspera(solicitud.fecha_recepcion)
  const urgente = esperandoMucho(solicitud, horas)
  const score = esRecibida ? scoreSolicitud(solicitud, pauta, horas) : null

  if (editing) {
    return (
      <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-3">
        <span className="text-sm font-medium text-muted-foreground">Editando solicitud…</span>
        <Input
          placeholder="Título (opcional)"
          value={editTitulo}
          onChange={(e) => setEditTitulo(e.target.value)}
        />
        <Textarea rows={3} value={editTexto} onChange={(e) => setEditTexto(e.target.value)} required />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={editPrioridad}
            onChange={(e) => setEditPrioridad(e.target.checked)}
          />
          Prioridad manual
        </label>
        <div className="flex gap-2">
          <Button
            size="sm"
            disabled={isActing}
            onClick={() => {
              const payload: SolicitudEditInput = {
                texto: editTexto,
                prioridad_manual: editPrioridad,
              }
              if (editTitulo.trim()) payload.titulo = editTitulo.trim()
              onGuardarEdicion(solicitud.id, payload)
              setEditing(false)
            }}
          >
            <Check /> Guardar
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>
            <X /> Cancelar
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`flex flex-col gap-2 rounded-lg border p-3 ${
        esPublicada
          ? 'border-border bg-card'
          : esEnCurso
            ? 'border-brand/40 bg-card'
            : urgente
              ? 'border-danger/40 bg-card'
              : 'border-border bg-card'
      }`}
      title={esRecibida ? motivoPrioridadCorto(solicitud, pauta) : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{clienteNombre}</span>
          {solicitud.prioridad_manual && <Flag className="size-3.5 text-warning" />}
          {score && (
            <span className="text-xs text-muted-foreground" title={score.label}>
              {score.emoji}
            </span>
          )}
        </div>
        <span className="shrink-0 text-xs text-muted-foreground">
          {formatFechaHoraNegocio(solicitud.fecha_recepcion)}
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {esRecibida && (
          <span
            className={`rounded-full px-2 py-0.5 text-xs ${
              urgente ? 'bg-danger-bg text-danger' : 'bg-muted text-muted-foreground'
            }`}
          >
            ⏱ {formatHoras(horas)}
          </span>
        )}
        {esEnCurso && (
          <span className="rounded-full bg-brand/10 px-2 py-0.5 text-xs text-brand">🚀 En curso</span>
        )}
        {pauta && (
          <>
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {PAUTA_TIPO_LABELS[pauta.tipo]}
            </span>
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {pauta.publicaciones_restantes}/{pauta.publicaciones_contratadas} restantes
            </span>
            {esPublicada && (
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                {formatMoneda(pauta.peso_comercial)}
              </span>
            )}
          </>
        )}
      </div>

      {esRecibida && (
        <p className="text-xs text-muted-foreground">{motivoPrioridadCorto(solicitud, pauta)}</p>
      )}
      {solicitud.titulo && <p className="text-sm font-medium">{solicitud.titulo}</p>}
      <p className={`text-sm whitespace-pre-wrap ${esPublicada ? 'line-clamp-2' : ''}`}>{solicitud.texto}</p>

      {esRecibida && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {solicitud.pauta_id ? (
            <Button size="sm" disabled={isActing} onClick={() => onPublicar(solicitud.id)}>
              <Check /> Publicar
            </Button>
          ) : (
            <>
              <SelectNative
                className="h-8 w-auto max-w-[14rem] text-xs"
                value={selectedPautaId}
                onChange={(e) => setSelectedPautaId(e.target.value)}
              >
                <option value="">Elegir pauta…</option>
                {pautasVigentes.map((p) => (
                  <option key={p.id} value={p.id}>
                    {pautaOptionLabel(p, clientesById.get(p.client_id) ?? '(cliente desconocido)')}
                  </option>
                ))}
              </SelectNative>
              <Button
                variant="secondary"
                size="sm"
                disabled={isActing}
                onClick={() => onVincular(solicitud.id, selectedPautaId)}
              >
                <Link2 /> Vincular
              </Button>
            </>
          )}
          <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
            <Pencil /> Editar
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={isActing}
            onClick={() => onCancelar(solicitud.id)}
          >
            <X /> Cancelar
          </Button>
        </div>
      )}
    </div>
  )
}
