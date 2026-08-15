import { useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { Link } from 'react-router-dom'

import { cn } from '@/lib/utils'
import { formatMoneda } from '@/lib/format'
import type { RankingComercialItem } from '@/features/alertas/api'

export function StatCard({
  icon: Icon,
  valor,
  label,
  to,
  tone = 'default',
  deltaPct,
}: {
  icon: LucideIcon
  valor: string | number
  label: string
  to?: string
  tone?: 'default' | 'danger'
  /** % change vs. the prior period. Positive is shown as good (green), negative as bad (red) — only meaningful for money/count metrics, not for status counters like "pautas vencidas". */
  deltaPct?: number | null
}) {
  const content = (
    <>
      <Icon className={cn('size-4', tone === 'danger' ? 'text-danger' : 'text-muted-foreground')} />
      <span className={cn('text-lg font-semibold', tone === 'danger' && 'text-danger')}>{valor}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
      {deltaPct != null && (
        <span className={cn('flex items-center gap-0.5 text-xs', deltaPct >= 0 ? 'text-success' : 'text-danger')}>
          {deltaPct >= 0 ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />}
          {Math.abs(deltaPct)}% vs. mes anterior
        </span>
      )}
    </>
  )
  if (to) {
    return (
      <Link
        to={to}
        className="flex flex-col gap-1 rounded-lg border border-border bg-card p-3 transition-colors hover:border-brand/40 hover:bg-accent"
      >
        {content}
      </Link>
    )
  }
  return <div className="flex flex-col gap-1 rounded-lg border border-border bg-card p-3">{content}</div>
}

const ESTADO_COMERCIAL_LABELS: Record<string, string> = {
  saludable: 'Saludable',
  atencion: 'Atención',
  renovacion: 'Renovación',
  vencido: 'Vencido',
}

const ESTADO_COMERCIAL_BADGE: Record<string, string> = {
  saludable: 'bg-success-bg text-success',
  atencion: 'bg-warning-bg text-warning',
  renovacion: 'bg-chart-gastos/10 text-chart-gastos',
  vencido: 'bg-muted text-muted-foreground',
}

export function RankingList({
  items,
  emptyMessage,
  onClienteClick,
}: {
  items: RankingComercialItem[]
  emptyMessage: string
  onClienteClick?: (clienteId: string) => void
}) {
  if (items.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">{emptyMessage}</p>
  }
  const maxPeso = Math.max(...items.map((i) => Number(i.peso_comercial)))
  return (
    <div className="flex flex-col divide-y divide-border">
      {items.map((item, index) => {
        const pct = maxPeso > 0 ? Math.round((Number(item.peso_comercial) / maxPeso) * 100) : 0
        return (
          <button
            key={item.cliente.id}
            type="button"
            onClick={() => onClienteClick?.(item.cliente.id)}
            className="flex items-center gap-3 py-2.5 text-left text-sm transition-colors hover:bg-accent"
          >
            <span className="w-5 shrink-0 text-muted-foreground">{index + 1}</span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="truncate font-medium">{item.cliente.nombre}</span>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${ESTADO_COMERCIAL_BADGE[item.estado_comercial] ?? 'bg-muted text-muted-foreground'}`}
                >
                  {ESTADO_COMERCIAL_LABELS[item.estado_comercial] ?? item.estado_comercial}
                </span>
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div className="h-full bg-brand" style={{ width: `${pct}%` }} />
              </div>
            </div>
            <div className="shrink-0 text-right">
              <p className="font-medium">{formatMoneda(item.valor_contratado)}</p>
              <p className="text-xs text-muted-foreground">Peso {formatMoneda(item.peso_comercial)}</p>
            </div>
          </button>
        )
      })}
    </div>
  )
}

// Was two <details> panels open side by side at all times ("Activos
// ahora" / "Histórico") — with few clients both showed nearly the same
// list twice; with many, both eating full vertical space permanently. A
// single toggle shows one list at a time, same total information.
export function RankingComercialSection({
  activos,
  historico,
  loading,
  onClienteClick,
}: {
  activos: RankingComercialItem[]
  historico: RankingComercialItem[]
  loading: boolean
  onClienteClick: (clienteId: string) => void
}) {
  const [tab, setTab] = useState<'activos' | 'historico'>('activos')
  const items = tab === 'activos' ? activos : historico
  const emptyMessage =
    tab === 'activos'
      ? 'Ningún cliente tiene un contrato vigente en este momento.'
      : 'Todavía no hay clientes con pautas.'

  return (
    <div className="flex flex-col gap-2">
      <div className="inline-flex w-fit rounded-lg border border-border bg-card p-1" role="tablist">
        {(['activos', 'historico'] as const).map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === key ? 'bg-brand text-brand-foreground' : 'text-muted-foreground hover:bg-accent'
            }`}
          >
            {key === 'activos' ? 'Activos ahora' : 'Histórico'} ({key === 'activos' ? activos.length : historico.length})
          </button>
        ))}
      </div>
      <div className="rounded-lg border border-border bg-card px-3">
        {loading ? (
          <p className="p-4 text-sm text-muted-foreground">Cargando…</p>
        ) : (
          <RankingList items={items} emptyMessage={emptyMessage} onClienteClick={onClienteClick} />
        )}
      </div>
    </div>
  )
}
