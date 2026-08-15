import { AlertTriangle, CheckCircle2, Clock, DollarSign, Inbox, Target } from 'lucide-react'

import type { Pauta } from '@/features/contratos/api'
import { formatMoneda, fechaNegocioISO } from '@/lib/format'
import type { Solicitud } from './api'
import { formatHoras, horasEnEspera, scoreSolicitud } from './utils'

function esClientePremium(clientId: string, pautas: Pauta[]): boolean {
  return pautas.some(
    (p) => p.client_id === clientId && p.vigente && (p.tipo === 'semestral' || p.tipo === 'anual'),
  )
}

function StatTile({ icon: Icon, valor, label }: { icon: typeof Inbox; valor: string | number; label: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-card p-3">
      <Icon className="size-4 text-muted-foreground" />
      <span className="text-lg font-semibold">{valor}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
}

export function MetricasSolicitudes({
  pendientes,
  publicadas,
  pautasById,
  pautas,
}: {
  pendientes: Solicitud[]
  publicadas: Solicitud[]
  pautasById: Map<string, Pauta>
  pautas: Pauta[]
}) {
  const pautaDe = (s: Solicitud) => (s.pauta_id ? (pautasById.get(s.pauta_id) ?? null) : null)

  const premiumPendientes = pendientes.filter((s) => {
    const pauta = pautaDe(s)
    return pauta && esClientePremium(pauta.client_id, pautas)
  }).length

  const valorPendiente = pendientes.reduce((acc, s) => {
    const pauta = pautaDe(s)
    return acc + (pauta ? Number(pauta.peso_comercial) : 0)
  }, 0)

  const hoyStr = fechaNegocioISO()
  const publicadasHoy = publicadas.filter((s) => fechaNegocioISO(s.fecha_recepcion) === hoyStr).length

  const horasPendientes = pendientes.map((s) => horasEnEspera(s.fecha_recepcion))
  const tiempoPromedio =
    horasPendientes.length > 0 ? horasPendientes.reduce((acc, h) => acc + h, 0) / horasPendientes.length : null

  const criticas = pendientes.filter((s) => scoreSolicitud(s, pautaDe(s), horasEnEspera(s.fecha_recepcion)).emoji === '🔥').length

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      <StatTile icon={Inbox} valor={pendientes.length} label="Pendientes" />
      <StatTile icon={Target} valor={premiumPendientes} label="Premium pendientes" />
      <StatTile icon={CheckCircle2} valor={publicadasHoy} label="Publicadas hoy" />
      <StatTile icon={DollarSign} valor={formatMoneda(valorPendiente)} label="Valor pendiente por publicar" />
      <StatTile
        icon={Clock}
        valor={tiempoPromedio === null ? '—' : formatHoras(tiempoPromedio).replace('hace ', '')}
        label="Espera promedio"
      />
      <StatTile icon={AlertTriangle} valor={criticas} label="Críticas" />
    </div>
  )
}
