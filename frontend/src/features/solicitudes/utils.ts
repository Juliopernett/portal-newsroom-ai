import { formatMoneda } from '@/lib/format'
import type { Pauta } from '@/features/contratos/api'
import type { Solicitud } from './api'

// Same threshold used across the legacy app to flag "waiting too long".
const STALE_REQUEST_HOURS = 4

export function horasEnEspera(fechaRecepcionIso: string): number {
  return (Date.now() - new Date(fechaRecepcionIso).getTime()) / 3_600_000
}

export function formatHoras(horas: number): string {
  if (horas < 1) return `hace ${Math.max(1, Math.round(horas * 60))} min`
  const h = Math.floor(horas)
  const m = Math.round((horas - h) * 60)
  return m > 0 ? `hace ${h}h ${m}m` : `hace ${h}h`
}

export function esperandoMucho(solicitud: Solicitud, horas: number): boolean {
  return solicitud.estado === 'recibida' && horas >= STALE_REQUEST_HOURS
}

export function motivoPrioridadCorto(solicitud: Solicitud, pauta: Pauta | null): string {
  if (solicitud.prioridad_manual) return '↑ Prioridad manual'
  if (!pauta) return '↑ Llegó primero — sin pauta vinculada (FIFO)'
  return `↑ Mayor peso comercial (${formatMoneda(pauta.peso_comercial)})`
}

export function scoreSolicitud(
  solicitud: Solicitud,
  pauta: Pauta | null,
  horas: number,
): { emoji: string; label: string } {
  if (solicitud.prioridad_manual || horas >= STALE_REQUEST_HOURS * 2) {
    return { emoji: '🔥', label: 'Alta prioridad' }
  }
  if ((pauta && Number(pauta.peso_comercial) > 0) || horas >= STALE_REQUEST_HOURS) {
    return { emoji: '🟠', label: 'Importante' }
  }
  return { emoji: '🟢', label: 'Normal' }
}

export function pautaOptionLabel(pauta: Pauta, clientNombre: string): string {
  const inicio = pauta.fecha_inicio.slice(0, 10)
  const fin = pauta.fecha_fin.slice(0, 10)
  return `${clientNombre} — ${inicio} a ${fin} — quedan ${pauta.publicaciones_restantes}/${pauta.publicaciones_contratadas}`
}
