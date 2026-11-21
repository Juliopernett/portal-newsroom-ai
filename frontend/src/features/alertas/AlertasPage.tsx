import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { PartyPopper, RefreshCw, Undo2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { AsesorIA } from './AsesorIA'
import { dashboardApi, insightsApi, type AlertaInteligente } from './api'
import {
  AccionSugeridaButtons,
  ActionItem,
  ContactarButton,
  EmptyState,
  HealthCard,
  OpportunityCategory,
  RadarRenovaciones,
  RenovarButton,
  VerClienteButton,
} from './components'
import { ALERTAS_OPORTUNIDAD, SEVERIDAD_EMOJI, centroAlertaKey, computarRadarBuckets, useDismissedAlerts } from './utils'
import { PAUTA_TIPO_LABELS } from '@/features/contratos/api'
import { formatFecha, formatMoneda } from '@/lib/format'

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="text-base font-semibold">{title}</h2>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {children}
    </section>
  )
}

type TabId = 'prioridades' | 'cobrar' | 'abandono' | 'dormidos' | 'renovaciones' | 'salud' | 'oportunidades'

interface TabDef {
  id: TabId
  label: string
  count: number
  tone: 'danger' | 'warning' | 'neutral'
}

// Una sola sección visible a la vez: cada pestaña lleva su contador (rojo/amarillo
// cuando hay algo que atender) para ver de un vistazo dónde hay trabajo sin recorrer
// una lista larguísima.
function TabsAlertas({ tabs, value, onChange }: { tabs: TabDef[]; value: TabId; onChange: (id: TabId) => void }) {
  const tono = (t: TabDef) =>
    t.count === 0
      ? 'bg-muted text-muted-foreground'
      : t.tone === 'danger'
        ? 'bg-danger-bg text-danger'
        : t.tone === 'warning'
          ? 'bg-warning-bg text-warning'
          : 'bg-muted text-foreground'
  return (
    <div
      role="tablist"
      aria-label="Secciones de alertas"
      className="sticky top-0 z-10 -mx-1 flex gap-2 overflow-x-auto bg-background px-1 py-2"
    >
      {tabs.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={value === t.id}
          onClick={() => onChange(t.id)}
          className={`flex shrink-0 items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition-colors ${
            value === t.id
              ? 'border-brand bg-brand/10 text-foreground'
              : 'border-border bg-card text-muted-foreground hover:bg-accent'
          }`}
        >
          {t.label}
          <span className={`rounded-full px-1.5 text-xs font-semibold ${tono(t)}`}>{t.count}</span>
        </button>
      ))}
    </div>
  )
}

// Muestra las primeras `limite` filas y deja ver el resto con un botón.
function Recortable({ children, limite = 8 }: { children: React.ReactNode[]; limite?: number }) {
  const [todo, setTodo] = useState(false)
  const filas = Array.isArray(children) ? children.flat() : [children]
  const visibles = todo ? filas : filas.slice(0, limite)
  return (
    <div className="flex flex-col gap-2">
      {visibles}
      {filas.length > limite && (
        <Button variant="ghost" size="sm" className="self-start" onClick={() => setTodo(!todo)}>
          {todo ? 'Ver menos' : `Ver las ${filas.length - limite} restantes`}
        </Button>
      )}
    </div>
  )
}

export function AlertasPage() {
  const centroQuery = useQuery({ queryKey: ['insights', 'centro-alertas'], queryFn: insightsApi.centroAlertas })
  const riesgoQuery = useQuery({ queryKey: ['insights', 'riesgo-abandono'], queryFn: insightsApi.riesgoAbandono })
  const cobrarQuery = useQuery({ queryKey: ['insights', 'cuentas-por-cobrar'], queryFn: insightsApi.cuentasPorCobrar })
  const dormidosQuery = useQuery({ queryKey: ['insights', 'dormidos'], queryFn: insightsApi.dormidos })
  const saludQuery = useQuery({ queryKey: ['insights', 'salud-clientes'], queryFn: insightsApi.saludClientes })
  const oportunidadesQuery = useQuery({ queryKey: ['insights', 'oportunidades'], queryFn: insightsApi.oportunidades })
  const dashAlertasQuery = useQuery({ queryKey: ['dashboard', 'alertas'], queryFn: dashboardApi.alertas })
  const rankingQuery = useQuery({ queryKey: ['dashboard', 'ranking'], queryFn: dashboardApi.ranking })
  const [radarBucket, setRadarBucket] = useState(0)
  const [tab, setTab] = useState<TabId>('prioridades')
  const { isDismissed, dismiss, dismissedCount, restoreAll } = useDismissedAlerts()

  const buckets = useMemo(() => computarRadarBuckets(rankingQuery.data ?? []), [rankingQuery.data])

  const centroAgrupado = useMemo(() => {
    const grupos = new Map<string, { item: AlertaInteligente; count: number }>()
    for (const item of centroQuery.data ?? []) {
      const key = centroAlertaKey(item)
      const existente = grupos.get(key)
      if (existente) existente.count += 1
      else grupos.set(key, { item, count: 1 })
    }
    return [...grupos.values()].filter(({ item }) => !isDismissed(centroAlertaKey(item)))
  }, [centroQuery.data, isDismissed])

  const riesgoVisible = (riesgoQuery.data ?? []).filter((r) => !isDismissed(`riesgo::${r.cliente.id}`))
  const cobrarVisible = (cobrarQuery.data ?? []).filter((c) => !isDismissed(`cobrar::${c.pauta_id}`))
  const dormidosVisible = (dormidosQuery.data ?? []).filter((d) => !isDismissed(`dormido::${d.cliente.id}`))
  const patronesVisible = (oportunidadesQuery.data ?? []).filter(
    (o) => !isDismissed(`patron::${o.cliente.id}::${o.tipo}`),
  )

  const sinNovedades =
    !centroQuery.isLoading &&
    !riesgoQuery.isLoading &&
    !cobrarQuery.isLoading &&
    !dormidosQuery.isLoading &&
    !oportunidadesQuery.isLoading &&
    !rankingQuery.isLoading &&
    centroAgrupado.length === 0 &&
    riesgoVisible.length === 0 &&
    cobrarVisible.length === 0 &&
    dormidosVisible.length === 0 &&
    patronesVisible.length === 0 &&
    buckets.every((b) => b.items.length === 0)

  const isFetching =
    centroQuery.isFetching ||
    riesgoQuery.isFetching ||
    cobrarQuery.isFetching ||
    dormidosQuery.isFetching ||
    saludQuery.isFetching ||
    oportunidadesQuery.isFetching ||
    dashAlertasQuery.isFetching ||
    rankingQuery.isFetching

  function refetchAll() {
    centroQuery.refetch()
    riesgoQuery.refetch()
    cobrarQuery.refetch()
    dormidosQuery.refetch()
    saludQuery.refetch()
    oportunidadesQuery.refetch()
    dashAlertasQuery.refetch()
    rankingQuery.refetch()
  }

  const totalCobrar = cobrarVisible.reduce((suma, c) => suma + Number(c.saldo_pendiente), 0)
  const tabs: TabDef[] = [
    {
      id: 'prioridades',
      label: 'Prioridades',
      count: centroAgrupado.length,
      tone: centroAgrupado.some(({ item }) => item.severidad === 'critica') ? 'danger' : 'warning',
    },
    { id: 'cobrar', label: 'Cuentas por cobrar', count: cobrarVisible.length, tone: 'warning' },
    { id: 'abandono', label: 'Riesgo de abandono', count: riesgoVisible.length, tone: 'danger' },
    { id: 'dormidos', label: 'Dormidos', count: dormidosVisible.length, tone: 'warning' },
    {
      id: 'renovaciones',
      label: 'Renovaciones',
      count: buckets.reduce((n, b) => n + b.items.length, 0),
      tone: 'neutral',
    },
    { id: 'salud', label: 'Salud de clientes', count: (saludQuery.data ?? []).length, tone: 'neutral' },
    { id: 'oportunidades', label: 'Oportunidades', count: patronesVisible.length, tone: 'neutral' },
  ]

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">Alertas</h1>
          <p className="text-sm text-muted-foreground">Recomendaciones accionables — no solo números</p>
        </div>
        <div className="flex items-center gap-2">
          {dismissedCount > 0 && (
            <Button variant="ghost" size="sm" onClick={restoreAll}>
              <Undo2 /> Restaurar {dismissedCount} descartada{dismissedCount === 1 ? '' : 's'}
            </Button>
          )}
          <Button variant="outline" size="icon" aria-label="Actualizar" onClick={refetchAll}>
            <RefreshCw className={isFetching ? 'animate-spin' : ''} />
          </Button>
        </div>
      </div>

      <AsesorIA />

      {sinNovedades && (
        <div className="flex items-center gap-3 rounded-lg border border-success/30 bg-success-bg p-4 text-success">
          <PartyPopper className="size-5 shrink-0" />
          <p className="text-sm font-medium">¡Todo al día! Ningún cliente necesita atención en este momento.</p>
        </div>
      )}

      <TabsAlertas tabs={tabs} value={tab} onChange={setTab} />

      {tab === 'prioridades' && (
      <Section title="Centro de Alertas">
        {centroQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : centroAgrupado.length === 0 ? (
          <EmptyState emoji="✅" mensaje="Sin pendientes urgentes — todo al día." />
        ) : (
          <Recortable>
            {centroAgrupado.map(({ item, count }) => (
              <ActionItem
                key={centroAlertaKey(item)}
                emoji={SEVERIDAD_EMOJI[item.severidad]}
                severidad={item.severidad === 'critica' ? 'danger' : item.severidad === 'atencion' ? 'warning' : 'success'}
                count={count}
                actions={
                  <AccionSugeridaButtons cliente={item.cliente} accion={item.accion} mensaje={item.mensaje} />
                }
                onDescartar={() => dismiss(centroAlertaKey(item))}
              >
                {item.mensaje}
              </ActionItem>
            ))}
          </Recortable>
        )}
      </Section>
      )}

      {tab === 'renovaciones' && (
      <Section title="Radar de Renovaciones">
        {rankingQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : (
          <RadarRenovaciones buckets={buckets} selected={radarBucket} onSelect={setRadarBucket} />
        )}
      </Section>
      )}

      {tab === 'abandono' && (
      <Section title="Riesgo de Abandono" subtitle="Tienen cupo pagado sin usar, pero llevan demasiado tiempo en silencio.">
        {riesgoQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : riesgoVisible.length === 0 ? (
          <EmptyState emoji="✅" mensaje="Ningún cliente vigente lleva demasiado tiempo en silencio." />
        ) : (
          <Recortable>
            {riesgoVisible.map((item) => (
              <ActionItem
                key={item.cliente.id}
                emoji="⚠️"
                severidad="danger"
                onDescartar={() => dismiss(`riesgo::${item.cliente.id}`)}
                actions={
                  <>
                    <VerClienteButton clienteId={item.cliente.id} />
                    <ContactarButton
                      telefono={item.cliente.telefono}
                      mensaje={`Hola ${item.cliente.nombre}, notamos que no nos has enviado material últimamente — ¿tienes algo para publicar? Todavía tienes ${item.publicaciones_restantes} publicaciones disponibles.`}
                    />
                  </>
                }
              >
                {item.cliente.nombre}: hace {item.dias_sin_actividad} días no envía material. Tiene{' '}
                {item.publicaciones_restantes} publicaciones disponibles.
              </ActionItem>
            ))}
          </Recortable>
        )}
      </Section>
      )}

      {tab === 'cobrar' && (
      <Section title="Cuentas por Cobrar" subtitle={`Total por cobrar: ${formatMoneda(totalCobrar)}. Pagaron una parte y falta el resto; el detalle agrupado por cliente está en Deudores.`}>
        {cobrarQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : cobrarVisible.length === 0 ? (
          <EmptyState emoji="✅" mensaje="Ningún cliente tiene saldo pendiente." />
        ) : (
          <Recortable>
            {cobrarVisible.map((item) => (
              <ActionItem
                key={item.pauta_id}
                emoji="💰"
                severidad="warning"
                onDescartar={() => dismiss(`cobrar::${item.pauta_id}`)}
                actions={
                  <>
                    <VerClienteButton clienteId={item.cliente.id} />
                    <ContactarButton
                      telefono={item.cliente.telefono}
                      mensaje={`Hola ${item.cliente.nombre}, te escribimos de Portal Vallenato — tienes un saldo pendiente de ${formatMoneda(item.saldo_pendiente)} de tu plan ${PAUTA_TIPO_LABELS[item.tipo]}. ¿Puedes completar el pago?`}
                    />
                  </>
                }
              >
                {item.cliente.nombre}: debe {formatMoneda(item.saldo_pendiente)} de su plan{' '}
                {PAUTA_TIPO_LABELS[item.tipo]} ({formatFecha(item.fecha_fin)}).
              </ActionItem>
            ))}
          </Recortable>
        )}
      </Section>
      )}

      {tab === 'dormidos' && (
      <Section title="Clientes Dormidos" subtitle="Sin ningún contrato vigente y sin actividad hace más de 60 días.">
        {dormidosQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : dormidosVisible.length === 0 ? (
          <EmptyState emoji="✅" mensaje="No hay clientes dormidos por ahora." />
        ) : (
          <Recortable>
            {dormidosVisible.map((item) => (
              <ActionItem
                key={item.cliente.id}
                emoji="💤"
                severidad="warning"
                onDescartar={() => dismiss(`dormido::${item.cliente.id}`)}
                actions={
                  <>
                    <VerClienteButton clienteId={item.cliente.id} />
                    <RenovarButton clienteId={item.cliente.id} label="Reactivar" />
                    <ContactarButton
                      telefono={item.cliente.telefono}
                      mensaje={`Hola ${item.cliente.nombre}, notamos que hace ${item.dias_sin_actividad} días no tienes actividad con nosotros — ¿qué ha pasado? Cuéntanos si podemos ayudarte a retomar tus publicaciones.`}
                    />
                  </>
                }
              >
                {item.cliente.nombre}: hace {item.dias_sin_actividad} días sin actividad. Último contrato{' '}
                {PAUTA_TIPO_LABELS[item.ultimo_contrato_tipo]}, venció {formatFecha(item.ultimo_contrato_fecha_fin)}.
              </ActionItem>
            ))}
          </Recortable>
        )}
      </Section>
      )}

      {tab === 'salud' && (
      <Section title="Score de Salud del Cliente">
        {saludQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : (saludQuery.data ?? []).length === 0 ? (
          <EmptyState emoji="✅" mensaje="Ningún cliente con pautas todavía." />
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {saludQuery.data!.map((item) => (
              <HealthCard
                key={item.cliente.id}
                cliente={item.cliente}
                nivel={item.nivel}
                estrellas={item.estrellas}
                score={item.score}
              />
            ))}
          </div>
        )}
      </Section>
      )}

      {tab === 'oportunidades' && (
      <Section title="Oportunidades Comerciales">
        <h3 className="text-sm font-medium text-muted-foreground">Categorías generales</h3>
        {dashAlertasQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {ALERTAS_OPORTUNIDAD.map((cfg) => (
              <OpportunityCategory
                key={cfg.id}
                label={cfg.label}
                tone={cfg.tone}
                clients={dashAlertasQuery.data?.[cfg.campo] ?? []}
              />
            ))}
          </div>
        )}

        <h3 className="mt-2 text-sm font-medium text-muted-foreground">Patrones detectados</h3>
        {oportunidadesQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : patronesVisible.length === 0 ? (
          <EmptyState emoji="✅" mensaje="No se detectaron patrones de compra por ahora." />
        ) : (
          <Recortable>
            {patronesVisible.map((item) => (
              <ActionItem
                key={`${item.cliente.id}-${item.tipo}`}
                emoji="💡"
                severidad="success"
                actions={<VerClienteButton clienteId={item.cliente.id} />}
                onDescartar={() => dismiss(`patron::${item.cliente.id}::${item.tipo}`)}
              >
                {item.mensaje}
              </ActionItem>
            ))}
          </Recortable>
        )}
      </Section>
      )}
    </div>
  )
}
