import type { Pauta } from '@/features/contratos/api'
import type { OtroIngreso } from '@/features/gastos/otrosIngresosApi'
import type { RentabilidadMensual } from './api'

export const MESES_LABELS = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

export const MESES_ABREV = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

export function chartEjeXLabel(item: RentabilidadMensual): string {
  return `${MESES_ABREV[item.mes - 1]}'${String(item.anio).slice(2)}`
}

// "Renovaciones del mes"/"ingresos último mes"/"pautado este mes" aren't
// backend fields — computed here over Pautas already loaded in memory,
// same as the legacy app. "Ingresos" = money already collected
// (fecha_pago), never a projection; "renovaciones" = time-package
// (non-Individual) contracts whose fecha_fin falls in the current
// calendar month.
export function calcularRenovacionesDelMes(pautas: Pauta[]): number {
  const ahora = new Date()
  let total = 0
  for (const pauta of pautas) {
    if (pauta.tipo === 'individual') continue
    const fechaFin = new Date(pauta.fecha_fin + 'T00:00:00')
    if (fechaFin.getMonth() === ahora.getMonth() && fechaFin.getFullYear() === ahora.getFullYear()) {
      total += 1
    }
  }
  return total
}

export function calcularIngresosDelMes(pautas: Pauta[], offsetMeses: number): number {
  const ahora = new Date()
  const objetivo = new Date(ahora.getFullYear(), ahora.getMonth() + offsetMeses, 1)
  let total = 0
  for (const pauta of pautas) {
    const fechaPago = new Date(pauta.fecha_pago + 'T00:00:00')
    if (fechaPago.getMonth() === objetivo.getMonth() && fechaPago.getFullYear() === objetivo.getFullYear()) {
      total += Number(pauta.valor_pagado)
    }
  }
  return total
}

// Same "dinero ya cobrado" definition as calcularIngresosDelMes, but for
// income that never came from a Pauta (Facebook, AdSense…) — kept as a
// separate function rather than folded into the one above because
// "Pautado este mes" reuses that function too, and a Facebook payout
// isn't "pautado" by any reading of the word. Only "Ingresos último mes"
// adds this on top.
export function calcularOtrosIngresosDelMes(otrosIngresos: OtroIngreso[], offsetMeses: number): number {
  const ahora = new Date()
  const objetivo = new Date(ahora.getFullYear(), ahora.getMonth() + offsetMeses, 1)
  let total = 0
  for (const ingreso of otrosIngresos) {
    const fechaCobro = new Date(ingreso.fecha_cobro + 'T00:00:00')
    if (fechaCobro.getMonth() === objetivo.getMonth() && fechaCobro.getFullYear() === objetivo.getFullYear()) {
      total += Number(ingreso.monto)
    }
  }
  return total
}

// % change vs. the prior period — null when there's no baseline to compare
// against (division by zero), which the caller renders as "no data" rather
// than a misleading "+∞%" or "0%".
export function calcularDeltaPct(actual: number, anterior: number): number | null {
  if (anterior === 0) return null
  return Math.round(((actual - anterior) / Math.abs(anterior)) * 100)
}

export type RentabilidadPreset = 'este-mes' | 'trimestre' | 'este-anio'

function toIsoDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

// Quick date-range presets for the Rentabilidad filter — avoids picking
// two <input type=date> by hand for the ranges people actually ask for.
// "Últimos 12 meses" is covered separately by clearing the filter (the
// backend's own default), not a preset here.
export function rangoPreset(preset: RentabilidadPreset): { desde: string; hasta: string } {
  const hoy = new Date()
  switch (preset) {
    case 'este-mes':
      return { desde: toIsoDate(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: toIsoDate(hoy) }
    case 'trimestre':
      return { desde: toIsoDate(new Date(hoy.getFullYear(), hoy.getMonth() - 2, 1)), hasta: toIsoDate(hoy) }
    case 'este-anio':
      return { desde: toIsoDate(new Date(hoy.getFullYear(), 0, 1)), hasta: toIsoDate(hoy) }
  }
}
