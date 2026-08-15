import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { formatMoneda } from '@/lib/format'
import type { RentabilidadMensual } from './api'
import { chartEjeXLabel } from './utils'

const AXIS_TICK = { fontSize: 12, fill: 'var(--muted-foreground)' }

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium text-popover-foreground">{label}</p>
      {payload.map((p) => (
        <p key={p.name} className="flex items-center gap-1.5 text-muted-foreground">
          <span className="inline-block size-2 rounded-full" style={{ background: p.color }} />
          {p.name}: <span className="font-medium text-popover-foreground">{formatMoneda(p.value)}</span>
        </p>
      ))}
    </div>
  )
}

export function IngresosGastosChart({ data }: { data: RentabilidadMensual[] }) {
  if (data.length === 0) {
    return <p className="p-6 text-center text-sm text-muted-foreground">Todavía no hay datos para graficar.</p>
  }
  const rows = data.map((item) => ({
    mes: chartEjeXLabel(item),
    Ingresos: Number(item.ingresos),
    Gastos: Number(item.gastos),
  }))
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} barGap={4} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey="mes" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: 'var(--border)' }} />
        <YAxis
          tick={AXIS_TICK}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => formatMoneda(v)}
          width={72}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--muted)' }} />
        <Bar dataKey="Ingresos" fill="var(--brand)" radius={[4, 4, 0, 0]} maxBarSize={24} />
        <Bar dataKey="Gastos" fill="var(--chart-gastos)" radius={[4, 4, 0, 0]} maxBarSize={24} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// Rentabilidad: one series, color by sign (status, not identity — the
// bar's position above/below the baseline already carries the signal,
// so no legend here, unlike the chart above).
export function RentabilidadChart({ data }: { data: RentabilidadMensual[] }) {
  if (data.length === 0) {
    return <p className="p-6 text-center text-sm text-muted-foreground">Todavía no hay datos para graficar.</p>
  }
  const rows = data.map((item) => ({
    mes: chartEjeXLabel(item),
    Rentabilidad: Number(item.rentabilidad),
  }))
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <XAxis dataKey="mes" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: 'var(--border)' }} />
        <YAxis
          tick={AXIS_TICK}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => formatMoneda(v)}
          width={72}
        />
        <ReferenceLine y={0} stroke="var(--border)" />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--muted)' }} />
        <Bar dataKey="Rentabilidad" radius={[4, 4, 4, 4]} maxBarSize={24}>
          {rows.map((row, i) => (
            <Cell key={i} fill={row.Rentabilidad >= 0 ? 'var(--success)' : 'var(--danger)'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
