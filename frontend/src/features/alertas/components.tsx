import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { ChevronDown, Eye, Phone, PlusCircle, RefreshCw, X } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import type { Client } from '@/features/clientes/api'
import { PAUTA_TIPO_LABELS, pautasApi } from '@/features/contratos/api'
import { formatFecha } from '@/lib/format'
import type { AccionSugerida, RankingComercialItem } from './api'
import { NIVEL_SALUD_BADGE, NIVEL_SALUD_LABELS, renderEstrellas, waLink, type RenewalBucket } from './utils'
import type { NivelSalud } from './api'

export function EmptyState({ emoji, mensaje }: { emoji: string; mensaje: string }) {
  return (
    <p className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
      <span>{emoji}</span> {mensaje}
    </p>
  )
}

export function ActionItem({
  emoji,
  severidad,
  children,
  actions,
  count,
  onDescartar,
}: {
  emoji: string
  severidad: 'danger' | 'warning' | 'success'
  children: ReactNode
  actions?: ReactNode
  count?: number
  onDescartar?: () => void
}) {
  const border = { danger: 'border-l-danger', warning: 'border-l-warning', success: 'border-l-success' }[severidad]
  return (
    <div className={`flex flex-wrap items-center gap-3 border-l-4 ${border} bg-card p-3 text-sm`}>
      <span>{emoji}</span>
      <span className="flex-1">
        {children}
        {count !== undefined && count > 1 && (
          <span className="ml-2 rounded-full bg-muted px-1.5 py-0.5 text-xs font-medium text-muted-foreground">
            ×{count}
          </span>
        )}
      </span>
      {actions && <span className="flex shrink-0 items-center gap-2">{actions}</span>}
      {onDescartar && (
        <button
          type="button"
          aria-label="Descartar"
          title="Descartar"
          onClick={onDescartar}
          className="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <X className="size-3.5" />
        </button>
      )}
    </div>
  )
}

export function VerClienteButton({ clienteId }: { clienteId: string }) {
  const navigate = useNavigate()
  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={() => navigate('/clientes', { state: { abrirFichaClientId: clienteId } })}
    >
      <Eye /> Ver cliente
    </Button>
  )
}

export function RenovarButton({ clienteId, label }: { clienteId: string; label: 'Renovar' | 'Reactivar' }) {
  const navigate = useNavigate()
  return (
    <Button size="sm" onClick={() => navigate('/contratos', { state: { preselectClientId: clienteId } })}>
      {label === 'Renovar' ? <RefreshCw /> : <PlusCircle />} {label}
    </Button>
  )
}

export function ContactarButton({ telefono, mensaje }: { telefono: string; mensaje?: string }) {
  const link = waLink(telefono, mensaje)
  if (!link) return null
  return (
    <Button size="sm" asChild>
      <a href={link} target="_blank" rel="noopener">
        <Phone /> Contactar
      </a>
    </Button>
  )
}

export function AccionSugeridaButtons({
  cliente,
  accion,
  mensaje,
}: {
  cliente: Client | null
  accion: AccionSugerida
  mensaje: string
}) {
  const navigate = useNavigate()
  return (
    <>
      {cliente && <VerClienteButton clienteId={cliente.id} />}
      {accion === 'renovar' && cliente && <RenovarButton clienteId={cliente.id} label="Renovar" />}
      {accion === 'reactivar' && cliente && <RenovarButton clienteId={cliente.id} label="Reactivar" />}
      {accion === 'contactar' && cliente && (
        <ContactarButton
          telefono={cliente.telefono}
          mensaje={`Hola ${cliente.nombre}, te escribimos de Portal Vallenato — ¿tienes alguna publicación para programar?`}
        />
      )}
      {accion === 'cobrar' && cliente && (
        <ContactarButton
          telefono={cliente.telefono}
          mensaje={`Hola ${cliente.nombre}, te escribimos de Portal Vallenato — ${mensaje.replace(`${cliente.nombre}: `, '')} ¿Puedes completar el pago?`}
        />
      )}
      {accion === 'ver_solicitudes' && (
        <Button variant="secondary" size="sm" onClick={() => navigate('/solicitudes')}>
          <Eye /> Ver
        </Button>
      )}
    </>
  )
}

export function RenewalCard({ item, dias }: { item: RankingComercialItem; dias: number }) {
  // The plain wa.me link every other ContactarButton uses can't include the
  // informe: that link is per-Pauta and minted on demand (a fresh, 15-day
  // token each time — see `pautasApi.crearInformeLink`), not a static URL,
  // so this one button needs its own async step before it can open wa.me.
  const informeLinkMutation = useMutation({
    mutationFn: pautasApi.crearInformeLink,
    onError: (err) => toast.error(errorMessage(err)),
  })

  function enviarRecordatorio() {
    informeLinkMutation.mutate(item.pauta_id, {
      onSuccess: (link) => {
        const mensaje = `Hola ${item.cliente.nombre}, tu plan ${PAUTA_TIPO_LABELS[item.tipo]} vence el ${formatFecha(item.fecha_vencimiento)}. Aquí tienes tu informe de resultados: ${link.url} ¿Quieres renovarlo?`
        const wa = waLink(item.cliente.telefono, mensaje)
        if (wa) window.open(wa, '_blank', 'noopener')
      },
    })
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <p className="text-sm font-medium">{item.cliente.nombre}</p>
      <p className="text-xs text-muted-foreground">
        {PAUTA_TIPO_LABELS[item.tipo]} · vence {formatFecha(item.fecha_vencimiento)} ({dias} día{dias === 1 ? '' : 's'})
      </p>
      <div className="flex flex-wrap gap-2">
        <VerClienteButton clienteId={item.cliente.id} />
        <RenovarButton clienteId={item.cliente.id} label="Renovar" />
        <Button size="sm" disabled={informeLinkMutation.isPending} onClick={enviarRecordatorio}>
          <Phone /> Contactar
        </Button>
      </div>
    </div>
  )
}

export function RadarRenovaciones({
  buckets,
  selected,
  onSelect,
}: {
  buckets: RenewalBucket[]
  selected: number
  onSelect: (index: number) => void
}) {
  const total = buckets.reduce((acc, b) => acc + b.items.length, 0)
  if (total === 0) return <EmptyState emoji="📅" mensaje="No hay renovaciones programadas por ahora." />

  const activo = buckets[selected] ?? buckets[0]

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Rango de vencimiento">
        {buckets.map((b, i) => (
          <button
            key={b.titulo}
            type="button"
            role="tab"
            aria-selected={i === selected}
            onClick={() => onSelect(i)}
            className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
              i === selected
                ? 'border-brand bg-brand/10 text-foreground'
                : 'border-border bg-card text-muted-foreground hover:bg-accent'
            }`}
          >
            <span>{b.emoji}</span>
            <span className="text-lg font-semibold">{b.items.length}</span>
            <span className="text-xs">{b.titulo}</span>
          </button>
        ))}
      </div>
      {activo.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin renovaciones en este rango.</p>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {activo.items.map(({ item, dias }) => (
            <RenewalCard key={item.cliente.id} item={item} dias={dias} />
          ))}
        </div>
      )}
    </div>
  )
}

export function HealthCard({ cliente, nivel, estrellas, score }: { cliente: Client; nivel: NivelSalud; estrellas: number; score: number }) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium">{cliente.nombre}</h3>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${NIVEL_SALUD_BADGE[nivel]}`}>
          {NIVEL_SALUD_LABELS[nivel]}
        </span>
      </div>
      <p className="text-amber-500">{renderEstrellas(estrellas)}</p>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">{score}%</p>
        <VerClienteButton clienteId={cliente.id} />
      </div>
    </div>
  )
}

export function OpportunityCategory({
  label,
  tone,
  clients,
}: {
  label: string
  tone: 'neutral' | 'success'
  clients: Client[]
}) {
  return (
    <details className="rounded-lg border border-border bg-card open:pb-2">
      <summary className="flex cursor-pointer list-none items-center gap-3 p-3">
        <span
          className={`flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
            tone === 'success' ? 'bg-success-bg text-success' : 'bg-muted text-muted-foreground'
          }`}
        >
          {clients.length}
        </span>
        <span className="flex-1 text-sm">{label}</span>
        <ChevronDown className="size-4 text-muted-foreground" />
      </summary>
      <div className="px-3">
        {clients.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin novedades.</p>
        ) : (
          clients.map((c) => (
            <div key={c.id} className="border-t border-border py-1.5 text-sm first:border-t-0">
              {c.nombre}
            </div>
          ))
        )}
      </div>
    </details>
  )
}
