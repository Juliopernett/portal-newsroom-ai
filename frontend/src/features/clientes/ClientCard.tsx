import { useNavigate } from 'react-router-dom'
import { Inbox, Pencil, Phone, Plus, RefreshCw, Eye } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { PAUTA_TIPO_LABELS } from '@/features/contratos/api'
import { cupoNivel, CUPO_BAR_COLOR } from '@/features/contratos/utils'
import type { RankingComercialItem } from '@/features/alertas/api'
import { formatFecha, formatMoneda } from '@/lib/format'
import type { Client } from './api'

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

export function ClientCard({
  client,
  item,
  onDetalle,
  onEditar,
}: {
  client: Client
  item: RankingComercialItem | undefined
  onDetalle: () => void
  onEditar: () => void
}) {
  const navigate = useNavigate()

  function irARegistrarPublicacion(e: React.MouseEvent) {
    e.stopPropagation()
    navigate('/solicitudes', { state: { prefillClientId: client.id } })
  }

  function irANuevaPauta(e: React.MouseEvent) {
    e.stopPropagation()
    navigate('/contratos', { state: { preselectClientId: client.id } })
  }

  if (!item) {
    return (
      <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4">
        <button type="button" className="flex flex-1 flex-col gap-2 text-left" onClick={onDetalle}>
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium">{client.nombre}</h3>
            <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              Sin pauta
            </span>
          </div>
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Phone className="size-3.5" />
            {client.telefono}
          </p>
        </button>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <Button variant="secondary" size="sm" onClick={irANuevaPauta}>
            <Plus /> Nueva pauta
          </Button>
          <Button variant="ghost" size="sm" onClick={onDetalle}>
            <Eye /> Detalle
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              onEditar()
            }}
          >
            <Pencil /> Editar
          </Button>
        </div>
      </div>
    )
  }

  const pct =
    item.publicaciones_contratadas > 0
      ? Math.round((item.publicaciones_restantes / item.publicaciones_contratadas) * 100)
      : 0
  const nivel = cupoNivel(item.publicaciones_restantes, item.publicaciones_contratadas, item.vigente)

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4" data-quota={nivel}>
      <button type="button" className="flex flex-1 flex-col gap-2 text-left" onClick={onDetalle}>
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-medium">{client.nombre}</h3>
          <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${ESTADO_COMERCIAL_BADGE[item.estado_comercial] ?? 'bg-muted text-muted-foreground'}`}>
            {ESTADO_COMERCIAL_LABELS[item.estado_comercial] ?? item.estado_comercial}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">Plan {PAUTA_TIPO_LABELS[item.tipo]}</p>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div className={`h-full ${CUPO_BAR_COLOR[nivel]}`} style={{ width: `${pct}%` }} />
        </div>
        <p className="text-sm">
          <strong>{item.publicaciones_restantes}</strong> de {item.publicaciones_contratadas} publicaciones
          disponibles
        </p>
        <p className="text-xs text-muted-foreground">Vence {formatFecha(item.fecha_vencimiento)}</p>
        <p className="text-sm font-medium">{formatMoneda(item.valor_contratado)} contratados</p>
        <p className="text-xs text-muted-foreground" title="Peso comercial — uso interno">
          Peso comercial: {formatMoneda(item.peso_comercial)}
        </p>
      </button>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={irARegistrarPublicacion}>
          <Inbox /> Registrar publicación
        </Button>
        <Button variant="secondary" size="sm" onClick={irANuevaPauta}>
          <RefreshCw /> Renovar
        </Button>
        <Button variant="ghost" size="sm" onClick={onDetalle}>
          <Eye /> Detalle
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation()
            onEditar()
          }}
        >
          <Pencil /> Editar
        </Button>
      </div>
    </div>
  )
}
