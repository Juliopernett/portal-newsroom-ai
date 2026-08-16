import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Inbox, Pencil, Phone, Plus, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { PAUTA_TIPO_LABELS, type Pauta } from '@/features/contratos/api'
import type { RankingComercialItem } from '@/features/alertas/api'
import type { Solicitud } from '@/features/solicitudes/api'
import { formatFecha, formatFechaHoraNegocio, formatMoneda, truncarTexto } from '@/lib/format'
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

interface Evento {
  fecha: string
  texto: string
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
      {children}
    </div>
  )
}

type FichaTab = 'actividad' | 'pautas' | 'solicitudes' | 'notas'

const FICHA_TABS: { id: FichaTab; label: string }[] = [
  { id: 'actividad', label: 'Actividad' },
  { id: 'pautas', label: 'Pautas' },
  { id: 'solicitudes', label: 'Solicitudes' },
  { id: 'notas', label: 'Notas' },
]

export function ClienteFicha({
  open,
  onOpenChange,
  client,
  item,
  pautasCliente,
  solicitudesPendientes,
  solicitudesPublicadas,
  onEditar,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  client: Client | null
  item: RankingComercialItem | undefined
  pautasCliente: Pauta[]
  solicitudesPendientes: Solicitud[]
  solicitudesPublicadas: Solicitud[]
  onEditar: () => void
}) {
  const navigate = useNavigate()
  const [tab, setTab] = useState<FichaTab>('actividad')

  // Actividad reciente is the default tab (not "Resumen" reordered into
  // last place) — it's the closest thing to an executive summary and used
  // to be buried at the bottom of a long scroll behind six other sections.
  // Reset on every client switch so the panel doesn't reopen mid-scroll on
  // whichever tab the previous client was left on.
  useEffect(() => {
    setTab('actividad')
  }, [client?.id])

  const ingresosGenerados = useMemo(
    () => pautasCliente.reduce((acc, p) => acc + Number(p.valor_pagado), 0),
    [pautasCliente],
  )

  const eventos = useMemo<Evento[]>(() => {
    if (!client) return []
    const items: Evento[] = [
      ...pautasCliente.map((p) => ({
        fecha: p.fecha_registro || p.fecha_inicio,
        texto: `Nueva pauta registrada — ${PAUTA_TIPO_LABELS[p.tipo]} (${p.publicaciones_contratadas} publicaciones)`,
      })),
      ...solicitudesPublicadas.map((s) => ({
        fecha: s.fecha_recepcion,
        texto: `Publicación registrada: "${truncarTexto(s.texto)}"`,
      })),
      ...solicitudesPendientes.map((s) => ({
        fecha: s.fecha_recepcion,
        texto: `Nueva solicitud recibida: "${truncarTexto(s.texto)}"`,
      })),
    ]
    return items.sort((a, b) => b.fecha.localeCompare(a.fecha))
  }, [client, pautasCliente, solicitudesPublicadas, solicitudesPendientes])

  if (!client) return null

  const publicadasVisibles = solicitudesPublicadas.slice(0, 15)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{client.nombre}</SheetTitle>
          <SheetDescription>Ficha comercial del cliente</SheetDescription>
        </SheetHeader>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" size="sm" onClick={onEditar}>
            <Pencil /> Editar
          </Button>
          <Button
            size="sm"
            onClick={() => navigate('/contratos', { state: { preselectClientId: client.id } })}
          >
            {item ? <RefreshCw /> : <Plus />} {item ? 'Renovar pauta' : 'Nueva pauta'}
          </Button>
        </div>

        <Section title="Resumen">
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="flex items-start justify-between gap-2">
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                  item ? (ESTADO_COMERCIAL_BADGE[item.estado_comercial] ?? 'bg-muted text-muted-foreground') : 'bg-muted text-muted-foreground'
                }`}
              >
                {item ? (ESTADO_COMERCIAL_LABELS[item.estado_comercial] ?? item.estado_comercial) : 'Sin pauta'}
              </span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {item && `${PAUTA_TIPO_LABELS[item.tipo]} · vence ${formatFecha(item.fecha_vencimiento)} · `}
              <span className="inline-flex items-center gap-1">
                <Phone className="size-3" /> {client.telefono}
              </span>
              {client.instagram && ` · @${client.instagram}`}
            </p>
            <div className={`mt-3 grid grid-cols-2 gap-2 ${item ? '' : 'max-w-[16rem]'}`}>
              {item && (
                <div className="rounded-md bg-muted p-2">
                  <p className="text-sm font-semibold">
                    {item.publicaciones_restantes} de {item.publicaciones_contratadas}
                  </p>
                  <p className="text-xs text-muted-foreground">Publicaciones restantes</p>
                </div>
              )}
              <div className="rounded-md bg-muted p-2">
                <p className="text-sm font-semibold">{formatMoneda(ingresosGenerados)}</p>
                <p className="text-xs text-muted-foreground">Ingresos generados</p>
              </div>
              {item && (
                <div className="rounded-md bg-muted p-2">
                  <p className="text-sm font-semibold">{formatMoneda(item.peso_comercial)}</p>
                  <p className="text-xs text-muted-foreground">Peso comercial</p>
                </div>
              )}
              <div className="rounded-md bg-muted p-2">
                <p className="text-sm font-semibold">{solicitudesPendientes.length}</p>
                <p className="text-xs text-muted-foreground">Solicitudes pendientes</p>
              </div>
            </div>
          </div>
        </Section>

        <div className="flex gap-1 border-b border-border" role="tablist" aria-label="Detalle del cliente">
          {FICHA_TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={`-mb-px border-b-2 px-2.5 py-2 text-sm font-medium transition-colors ${
                tab === t.id
                  ? 'border-brand text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'actividad' && (
          <Section title="Actividad reciente">
            {eventos.length === 0 ? (
              <p className="text-sm text-muted-foreground">🕐 Sin actividad todavía.</p>
            ) : (
              <div className="flex flex-col gap-2">
                {eventos.map((e, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs">
                    <span className="w-20 shrink-0 text-muted-foreground">{formatFecha(e.fecha)}</span>
                    <span className="h-4 w-px shrink-0 bg-border" />
                    <span className="pl-1">{e.texto}</span>
                  </div>
                ))}
              </div>
            )}
          </Section>
        )}

        {tab === 'pautas' && (
          <Section title="Historial de pautas">
            {pautasCliente.length === 0 ? (
              <p className="text-sm text-muted-foreground">📄 Este cliente todavía no tiene pautas.</p>
            ) : (
              <div className="flex flex-col divide-y divide-border rounded-lg border border-border">
                {pautasCliente.map((p) => (
                  <div key={p.id} className="flex items-center justify-between gap-2 p-2.5 text-sm">
                    <div>
                      <p>
                        {formatFecha(p.fecha_inicio)} – {formatFecha(p.fecha_fin)} · {PAUTA_TIPO_LABELS[p.tipo]}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {p.publicaciones_restantes}/{p.publicaciones_contratadas} ·{' '}
                        <span className={p.vigente ? 'text-success' : 'text-muted-foreground'}>
                          {p.vigente ? 'Vigente' : 'Vencido'}
                        </span>
                      </p>
                      {Number(p.saldo_pendiente) > 0 && (
                        <p className="text-xs font-medium text-danger">
                          Debe {formatMoneda(p.saldo_pendiente)}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate('/contratos', { state: { editPautaId: p.id } })}
                    >
                      <Pencil /> Editar
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Section>
        )}

        {tab === 'solicitudes' && (
          <div className="flex flex-col gap-4">
            <Section title="Solicitudes pendientes">
              {solicitudesPendientes.length === 0 ? (
                <p className="text-sm text-muted-foreground">✅ Sin solicitudes pendientes.</p>
              ) : (
                <div className="flex flex-col divide-y divide-border rounded-lg border border-border">
                  {solicitudesPendientes.map((s) => (
                    <div key={s.id} className="p-2.5 text-sm">
                      <p>{truncarTexto(s.texto, 60)}</p>
                      <p className="text-xs text-muted-foreground">{formatFechaHoraNegocio(s.fecha_recepcion)}</p>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            <Section title="Historial de publicaciones">
              {publicadasVisibles.length === 0 ? (
                <p className="text-sm text-muted-foreground">📭 Todavía no hay publicaciones.</p>
              ) : (
                <div className="flex flex-col divide-y divide-border rounded-lg border border-border">
                  {publicadasVisibles.map((s) => (
                    <div key={s.id} className="p-2.5 text-sm">
                      <p>{truncarTexto(s.texto, 40)}</p>
                      <p className="text-xs text-muted-foreground">{formatFechaHoraNegocio(s.fecha_recepcion)}</p>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          </div>
        )}

        {tab === 'notas' && (
          <Section title="Notas internas">
            <p className={`text-sm ${client.observaciones ? '' : 'text-muted-foreground italic'}`}>
              {client.observaciones || 'Sin notas internas todavía.'}
            </p>
          </Section>
        )}

        {item && (
          <Button
            variant="secondary"
            onClick={() => navigate('/solicitudes', { state: { prefillClientId: client.id } })}
          >
            <Inbox /> Registrar publicación
          </Button>
        )}
      </SheetContent>
    </Sheet>
  )
}
