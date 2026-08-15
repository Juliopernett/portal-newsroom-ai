import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, Eye, Phone, PlusCircle, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { Client } from '@/features/clientes/api'
import { PAUTA_TIPO_LABELS, type PautaTipo } from '@/features/contratos/api'
import { formatFecha } from '@/lib/format'
import type { AccionSugerida } from './api'
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
}: {
  emoji: string
  severidad: 'danger' | 'warning' | 'success'
  children: ReactNode
  actions?: ReactNode
}) {
  const border = { danger: 'border-l-danger', warning: 'border-l-warning', success: 'border-l-success' }[severidad]
  return (
    <div className={`flex flex-wrap items-center gap-3 border-l-4 ${border} bg-card p-3 text-sm`}>
      <span>{emoji}</span>
      <span className="flex-1">{children}</span>
      {actions && <span className="flex shrink-0 items-center gap-2">{actions}</span>}
    </div>
  )
}

export function VerClienteButton({ nombre }: { nombre?: string }) {
  const navigate = useNavigate()
  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={() => navigate('/clientes', nombre ? { state: { buscar: nombre } } : undefined)}
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

export function AccionSugeridaButtons({ cliente, accion }: { cliente: Client | null; accion: AccionSugerida }) {
  const navigate = useNavigate()
  return (
    <>
      {cliente && <VerClienteButton nombre={cliente.nombre} />}
      {accion === 'renovar' && cliente && <RenovarButton clienteId={cliente.id} label="Renovar" />}
      {accion === 'reactivar' && cliente && <RenovarButton clienteId={cliente.id} label="Reactivar" />}
      {accion === 'contactar' && cliente && (
        <ContactarButton
          telefono={cliente.telefono}
          mensaje={`Hola ${cliente.nombre}, te escribimos de Portal Vallenato — ¿tienes alguna publicación para programar?`}
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

export function RenewalCard({ item, dias }: { item: { cliente: Client; tipo: PautaTipo; fecha_vencimiento: string }; dias: number }) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <p className="text-sm font-medium">{item.cliente.nombre}</p>
      <p className="text-xs text-muted-foreground">
        {PAUTA_TIPO_LABELS[item.tipo]} · vence {formatFecha(item.fecha_vencimiento)} ({dias} día{dias === 1 ? '' : 's'})
      </p>
      <div className="flex flex-wrap gap-2">
        <VerClienteButton nombre={item.cliente.nombre} />
        <RenovarButton clienteId={item.cliente.id} label="Renovar" />
        <ContactarButton
          telefono={item.cliente.telefono}
          mensaje={`Hola ${item.cliente.nombre}, tu plan ${PAUTA_TIPO_LABELS[item.tipo]} vence el ${formatFecha(item.fecha_vencimiento)}. ¿Quieres renovarlo?`}
        />
      </div>
    </div>
  )
}

export function RadarRenovaciones({ buckets }: { buckets: RenewalBucket[] }) {
  const total = buckets.reduce((acc, b) => acc + b.items.length, 0)
  if (total === 0) return <EmptyState emoji="📅" mensaje="No hay renovaciones programadas por ahora." />
  return (
    <div className="flex flex-col gap-4">
      {buckets.map(({ titulo, items }) => (
        <div key={titulo}>
          <h3 className="mb-2 text-sm font-medium">{titulo}</h3>
          {items.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin renovaciones en este rango.</p>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {items.map(({ item, dias }) => (
                <RenewalCard key={item.cliente.id} item={item} dias={dias} />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export function HealthCard({ cliente, nivel, estrellas, score }: { cliente: Client; nivel: NivelSalud; estrellas: number; score: number }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-card p-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium">{cliente.nombre}</h3>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${NIVEL_SALUD_BADGE[nivel]}`}>
          {NIVEL_SALUD_LABELS[nivel]}
        </span>
      </div>
      <p className="text-amber-500">{renderEstrellas(estrellas)}</p>
      <p className="text-xs text-muted-foreground">{score}%</p>
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
