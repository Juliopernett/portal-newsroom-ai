import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  DollarSign,
  Inbox,
  RefreshCw,
  Target,
  Users,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { pautasApi } from '@/features/contratos/api'
import { otrosIngresosApi } from '@/features/gastos/otrosIngresosApi'
import { formatMoneda } from '@/lib/format'
import { dashboardApi } from './api'
import { IngresosGastosChart, RentabilidadChart } from './charts'
import { RankingComercialSection, StatCard } from './components'
import {
  MESES_LABELS,
  calcularDeltaPct,
  calcularIngresosDelMes,
  calcularOtrosIngresosDelMes,
  calcularRenovacionesDelMes,
  rangoPreset,
  type RentabilidadPreset,
} from './utils'

const RENTABILIDAD_PRESETS: { value: RentabilidadPreset; label: string }[] = [
  { value: 'este-mes', label: 'Este mes' },
  { value: 'trimestre', label: 'Último trimestre' },
  { value: 'este-anio', label: 'Este año' },
]

export function DashboardPage() {
  const navigate = useNavigate()
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')

  const resumenQuery = useQuery({ queryKey: ['dashboard', 'resumen'], queryFn: dashboardApi.resumen })
  const alertasQuery = useQuery({ queryKey: ['dashboard', 'alertas'], queryFn: dashboardApi.alertas })
  const rankingQuery = useQuery({ queryKey: ['dashboard', 'ranking'], queryFn: dashboardApi.ranking })
  const rentabilidadQuery = useQuery({
    queryKey: ['dashboard', 'rentabilidad', desde, hasta],
    queryFn: () => dashboardApi.rentabilidad(desde || undefined, hasta || undefined),
  })
  const pautasQuery = useQuery({ queryKey: ['pautas'], queryFn: pautasApi.list })
  const otrosIngresosQuery = useQuery({ queryKey: ['otros-ingresos'], queryFn: otrosIngresosApi.list })

  const isFetching =
    resumenQuery.isFetching ||
    alertasQuery.isFetching ||
    rankingQuery.isFetching ||
    rentabilidadQuery.isFetching ||
    otrosIngresosQuery.isFetching

  function refetchAll() {
    resumenQuery.refetch()
    alertasQuery.refetch()
    rankingQuery.refetch()
    rentabilidadQuery.refetch()
    pautasQuery.refetch()
    otrosIngresosQuery.refetch()
  }

  function abrirFicha(clienteId: string) {
    navigate('/clientes', { state: { abrirFichaClientId: clienteId } })
  }

  const pautas = pautasQuery.data ?? []
  const otrosIngresos = otrosIngresosQuery.data ?? []
  const renovacionesDelMes = useMemo(() => calcularRenovacionesDelMes(pautas), [pautas])
  // "Ingresos último mes" es el total real cobrado — pautas + lo que entra
  // fuera de una pauta (Facebook, AdSense…). "Pautado este mes" sigue
  // siendo solo pautas, ver calcularOtrosIngresosDelMes.
  const ingresosUltimoMes = useMemo(
    () => calcularIngresosDelMes(pautas, -1) + calcularOtrosIngresosDelMes(otrosIngresos, -1),
    [pautas, otrosIngresos],
  )
  const ingresosMesAnterior = useMemo(
    () => calcularIngresosDelMes(pautas, -2) + calcularOtrosIngresosDelMes(otrosIngresos, -2),
    [pautas, otrosIngresos],
  )
  const pautadoMesActual = useMemo(() => calcularIngresosDelMes(pautas, 0), [pautas])
  const pautadoMesAnterior = useMemo(() => calcularIngresosDelMes(pautas, -1), [pautas])
  const deltaIngresosUltimoMes = calcularDeltaPct(ingresosUltimoMes, ingresosMesAnterior)
  const deltaPautadoMesActual = calcularDeltaPct(pautadoMesActual, pautadoMesAnterior)

  const resumen = resumenQuery.data
  const pendientes = resumen?.solicitudes_pendientes ?? 0
  const antiguas = alertasQuery.data?.solicitudes_antiguas.length ?? 0
  const rankingActivos = (rankingQuery.data ?? []).filter((i) => i.vigente)

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Resumen comercial de Portal Vallenato</p>
        </div>
        <Button variant="outline" size="icon" aria-label="Actualizar" onClick={refetchAll}>
          <RefreshCw className={isFetching ? 'animate-spin' : ''} />
        </Button>
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">Solicitudes pendientes</h2>
        {resumenQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : pendientes === 0 ? (
          <div className="flex flex-wrap items-center gap-3 p-4">
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <CheckCircle2 className="size-4" /> No tienes solicitudes pendientes.
            </p>
            <Button variant="outline" size="sm" onClick={() => navigate('/solicitudes')}>
              <Inbox /> Ir a solicitudes
            </Button>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-card p-4">
            <div className="flex flex-col">
              <span className="text-2xl font-semibold">{pendientes}</span>
              <span className="text-sm text-muted-foreground">
                solicitud{pendientes === 1 ? '' : 'es'} pendiente{pendientes === 1 ? '' : 's'}
              </span>
            </div>
            {antiguas > 0 && (
              <p className="flex items-center gap-1.5 text-sm text-danger">
                <AlertTriangle className="size-4" />
                {antiguas} lleva{antiguas === 1 ? '' : 'n'} más de 4h esperando respuesta
              </p>
            )}
            <Button className="ml-auto" onClick={() => navigate('/solicitudes')}>
              <Inbox /> Ir a solicitudes
            </Button>
          </div>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-base font-semibold">Indicadores</h2>

        <div>
          {resumenQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
              <StatCard
                icon={AlertTriangle}
                valor={resumen!.pautas_vencidas}
                label="Pautas vencidas"
                to="/contratos"
                tone={resumen!.pautas_vencidas > 0 ? 'danger' : 'default'}
              />
              <StatCard icon={CheckCircle2} valor={resumen!.publicaciones_este_mes} label="Publicaciones este mes" to="/solicitudes" />
              <StatCard icon={RefreshCw} valor={renovacionesDelMes} label="Renovaciones del mes" to="/contratos" />
              <StatCard icon={Users} valor={resumen!.clientes_activos} label="Clientes activos" to="/clientes" />
              <StatCard icon={DollarSign} valor={formatMoneda(resumen!.ingreso_contratado_activo)} label="Ingresos año actual" />
              <StatCard
                icon={DollarSign}
                valor={formatMoneda(ingresosUltimoMes)}
                label="Ingresos último mes"
                deltaPct={deltaIngresosUltimoMes}
              />
              <StatCard
                icon={DollarSign}
                valor={formatMoneda(pautadoMesActual)}
                label="Pautado este mes"
                deltaPct={deltaPautadoMesActual}
              />
              <StatCard icon={Target} valor={formatMoneda(resumen!.peso_comercial_promedio)} label="Peso comercial promedio" />
              <StatCard icon={DollarSign} valor={formatMoneda(resumen!.valor_promedio_por_cliente)} label="Valor promedio/cliente" />
              <StatCard icon={DollarSign} valor={formatMoneda(resumen!.ingreso_historico)} label="Ingreso histórico" />
            </div>
          )}
        </div>

        <div className="min-w-0">
          <div className="mb-2 flex min-w-0 flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-end lg:justify-between">
            <div className="min-w-0">
              <h3 className="text-sm font-medium text-muted-foreground">Rentabilidad mensual</h3>
              <p className="text-xs text-muted-foreground">
                {desde || hasta ? 'Rango seleccionado' : 'Últimos 12 meses'} — ingresos cobrados menos gastos registrados
              </p>
            </div>
            {/* min-w-0 at every flex level here on purpose: Safari's native
                <input type=date> refuses to shrink below its own intrinsic
                content width unless every ancestor flex container explicitly
                overrides the default min-width:auto — otherwise the date
                field pushes this row wider than the page (confirmed on
                iPhone Safari; Chrome tolerates the same markup fine). */}
            <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
              <div className="flex flex-wrap gap-1">
                {RENTABILIDAD_PRESETS.map((p) => (
                  <Button
                    key={p.value}
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      const { desde: d, hasta: h } = rangoPreset(p.value)
                      setDesde(d)
                      setHasta(h)
                    }}
                  >
                    {p.label}
                  </Button>
                ))}
              </div>
              <div className="flex min-w-0 w-full flex-col gap-1 sm:w-auto">
                <Label htmlFor="dashboard-rentabilidad-desde" className="text-xs">Desde</Label>
                <Input
                  id="dashboard-rentabilidad-desde"
                  type="date"
                  className="h-8 min-w-0 w-full"
                  value={desde}
                  onChange={(e) => setDesde(e.target.value)}
                />
              </div>
              <div className="flex min-w-0 w-full flex-col gap-1 sm:w-auto">
                <Label htmlFor="dashboard-rentabilidad-hasta" className="text-xs">Hasta</Label>
                <Input
                  id="dashboard-rentabilidad-hasta"
                  type="date"
                  className="h-8 min-w-0 w-full"
                  value={hasta}
                  onChange={(e) => setHasta(e.target.value)}
                />
              </div>
              {(desde || hasta) && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full sm:w-auto"
                  onClick={() => {
                    setDesde('')
                    setHasta('')
                  }}
                >
                  Últimos 12 meses
                </Button>
              )}
            </div>
          </div>
          {rentabilidadQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="text-sm font-medium">Ingresos vs. gastos</h4>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <span className="inline-block size-2 rounded-full bg-brand" /> Ingresos
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="inline-block size-2 rounded-full bg-chart-gastos" /> Gastos
                    </span>
                  </div>
                </div>
                <IngresosGastosChart data={rentabilidadQuery.data ?? []} />
              </div>
              <div className="rounded-lg border border-border bg-card p-4">
                <h4 className="mb-2 text-sm font-medium">Rentabilidad</h4>
                <RentabilidadChart data={rentabilidadQuery.data ?? []} />
              </div>

              <details className="rounded-lg border border-border bg-card">
                <summary className="cursor-pointer p-3 text-sm font-medium">Ver como tabla</summary>
                <div className="flex flex-col divide-y divide-border px-3 pb-2">
                  {(rentabilidadQuery.data ?? []).map((item) => {
                    const esPositiva = Number(item.rentabilidad) >= 0
                    return (
                      <div key={`${item.anio}-${item.mes}`} className="flex flex-wrap items-center gap-4 py-2 text-sm">
                        <span className="w-32 shrink-0 font-medium">
                          {MESES_LABELS[item.mes - 1]} {item.anio}
                        </span>
                        <span className="text-muted-foreground">Ingresos {formatMoneda(item.ingresos)}</span>
                        <span className="text-muted-foreground">Gastos {formatMoneda(item.gastos)}</span>
                        <span className={esPositiva ? 'text-success' : 'text-danger'}>
                          Rentabilidad {formatMoneda(item.rentabilidad)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </details>
            </div>
          )}
        </div>

        <div>
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">Ranking comercial</h3>
          <RankingComercialSection
            activos={rankingActivos}
            historico={rankingQuery.data ?? []}
            loading={rankingQuery.isLoading}
            onClienteClick={abrirFicha}
          />
        </div>

      </section>
    </div>
  )
}
