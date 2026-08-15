import type { LucideIcon } from 'lucide-react'

import { formatMoneda } from '@/lib/format'
import type { RankingComercialItem } from '@/features/alertas/api'

export function StatCard({ icon: Icon, valor, label }: { icon: LucideIcon; valor: string | number; label: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-card p-3">
      <Icon className="size-4 text-muted-foreground" />
      <span className="text-lg font-semibold">{valor}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
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

export function RankingList({ items, emptyMessage }: { items: RankingComercialItem[]; emptyMessage: string }) {
  if (items.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">{emptyMessage}</p>
  }
  const maxPeso = Math.max(...items.map((i) => Number(i.peso_comercial)))
  return (
    <div className="flex flex-col divide-y divide-border">
      {items.map((item, index) => {
        const pct = maxPeso > 0 ? Math.round((Number(item.peso_comercial) / maxPeso) * 100) : 0
        return (
          <div key={item.cliente.id} className="flex items-center gap-3 py-2.5 text-sm">
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
          </div>
        )
      })}
    </div>
  )
}
