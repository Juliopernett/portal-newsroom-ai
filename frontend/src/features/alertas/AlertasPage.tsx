import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { dashboardApi, insightsApi } from './api'
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
import { ALERTAS_OPORTUNIDAD, SEVERIDAD_EMOJI, computarRadarBuckets } from './utils'
import { PAUTA_TIPO_LABELS } from '@/features/contratos/api'
import { formatFecha } from '@/lib/format'

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

export function AlertasPage() {
  const centroQuery = useQuery({ queryKey: ['insights', 'centro-alertas'], queryFn: insightsApi.centroAlertas })
  const riesgoQuery = useQuery({ queryKey: ['insights', 'riesgo-abandono'], queryFn: insightsApi.riesgoAbandono })
  const dormidosQuery = useQuery({ queryKey: ['insights', 'dormidos'], queryFn: insightsApi.dormidos })
  const saludQuery = useQuery({ queryKey: ['insights', 'salud-clientes'], queryFn: insightsApi.saludClientes })
  const oportunidadesQuery = useQuery({ queryKey: ['insights', 'oportunidades'], queryFn: insightsApi.oportunidades })
  const dashAlertasQuery = useQuery({ queryKey: ['dashboard', 'alertas'], queryFn: dashboardApi.alertas })
  const rankingQuery = useQuery({ queryKey: ['dashboard', 'ranking'], queryFn: dashboardApi.ranking })

  const buckets = useMemo(() => computarRadarBuckets(rankingQuery.data ?? []), [rankingQuery.data])

  const isFetching =
    centroQuery.isFetching ||
    riesgoQuery.isFetching ||
    dormidosQuery.isFetching ||
    saludQuery.isFetching ||
    oportunidadesQuery.isFetching ||
    dashAlertasQuery.isFetching ||
    rankingQuery.isFetching

  function refetchAll() {
    centroQuery.refetch()
    riesgoQuery.refetch()
    dormidosQuery.refetch()
    saludQuery.refetch()
    oportunidadesQuery.refetch()
    dashAlertasQuery.refetch()
    rankingQuery.refetch()
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">Alertas</h1>
          <p className="text-sm text-muted-foreground">Recomendaciones accionables — no solo números</p>
        </div>
        <Button variant="outline" size="icon" aria-label="Actualizar" onClick={refetchAll}>
          <RefreshCw className={isFetching ? 'animate-spin' : ''} />
        </Button>
      </div>

      <Section title="Centro de Alertas">
        {centroQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : (centroQuery.data ?? []).length === 0 ? (
          <EmptyState emoji="✅" mensaje="Sin pendientes urgentes — todo al día." />
        ) : (
          <div className="flex flex-col gap-2">
            {centroQuery.data!.map((item, i) => (
              <ActionItem
                key={i}
                emoji={SEVERIDAD_EMOJI[item.severidad]}
                severidad={item.severidad === 'critica' ? 'danger' : item.severidad === 'atencion' ? 'warning' : 'success'}
                actions={<AccionSugeridaButtons cliente={item.cliente} accion={item.accion} />}
              >
                {item.mensaje}
              </ActionItem>
            ))}
          </div>
        )}
      </Section>

      <Section title="Radar de Renovaciones">
        {rankingQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-3">
              {buckets.map((b) => (
                <div key={b.titulo} className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
                  <span>{b.emoji}</span>
                  <span className="text-lg font-semibold">{b.items.length}</span>
                  <span className="text-xs text-muted-foreground">{b.titulo}</span>
                </div>
              ))}
            </div>
            <RadarRenovaciones buckets={buckets} />
          </>
        )}
      </Section>

      <Section title="Riesgo de Abandono" subtitle="Tienen cupo pagado sin usar, pero llevan demasiado tiempo en silencio.">
        {riesgoQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : (riesgoQuery.data ?? []).length === 0 ? (
          <EmptyState emoji="✅" mensaje="Ningún cliente vigente lleva demasiado tiempo en silencio." />
        ) : (
          <div className="flex flex-col gap-2">
            {riesgoQuery.data!.map((item) => (
              <ActionItem
                key={item.cliente.id}
                emoji="⚠️"
                severidad="danger"
                actions={
                  <>
                    <VerClienteButton />
                    <ContactarButton telefono={item.cliente.telefono} />
                  </>
                }
              >
                {item.cliente.nombre}: hace {item.dias_sin_actividad} días no envía material. Tiene{' '}
                {item.publicaciones_restantes} publicaciones disponibles.
              </ActionItem>
            ))}
          </div>
        )}
      </Section>

      <Section title="Clientes Dormidos" subtitle="Sin ningún contrato vigente y sin actividad hace más de 60 días.">
        {dormidosQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : (dormidosQuery.data ?? []).length === 0 ? (
          <EmptyState emoji="✅" mensaje="No hay clientes dormidos por ahora." />
        ) : (
          <div className="flex flex-col gap-2">
            {dormidosQuery.data!.map((item) => (
              <ActionItem
                key={item.cliente.id}
                emoji="💤"
                severidad="warning"
                actions={
                  <>
                    <VerClienteButton />
                    <RenovarButton clienteId={item.cliente.id} label="Reactivar" />
                  </>
                }
              >
                {item.cliente.nombre}: hace {item.dias_sin_actividad} días sin actividad. Último contrato{' '}
                {PAUTA_TIPO_LABELS[item.ultimo_contrato_tipo]}, venció {formatFecha(item.ultimo_contrato_fecha_fin)}.
              </ActionItem>
            ))}
          </div>
        )}
      </Section>

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
        ) : (oportunidadesQuery.data ?? []).length === 0 ? (
          <EmptyState emoji="✅" mensaje="No se detectaron patrones de compra por ahora." />
        ) : (
          <div className="flex flex-col gap-2">
            {oportunidadesQuery.data!.map((item, i) => (
              <ActionItem key={i} emoji="💡" severidad="success" actions={<VerClienteButton />}>
                {item.mensaje}
              </ActionItem>
            ))}
          </div>
        )}
      </Section>
    </div>
  )
}
