import type { Pauta } from '@/features/contratos/api'
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
