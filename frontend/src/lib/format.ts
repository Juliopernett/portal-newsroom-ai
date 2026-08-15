export function formatMoneda(valor: string | number): string {
  return '$' + Number(valor).toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

export function formatFecha(iso: string): string {
  return iso ? iso.slice(0, 10) : ''
}

const NEGOCIO_TZ = 'America/Bogota'

// Portal Vallenato operates in Colombia (UTC-5) but the backend stores
// timestamps in UTC — showing that raw string runs the displayed time
// 5h ahead of the real business time.
export function formatFechaHoraNegocio(iso: string): string {
  if (!iso) return ''
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: NEGOCIO_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(iso))
}

export function fechaNegocioISO(iso?: string): string {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: NEGOCIO_TZ }).format(
    iso ? new Date(iso) : new Date(),
  )
}

// Pure calendar-day arithmetic anchored to UTC midnight — avoids the
// browser's local timezone shifting the result by a day.
export function sumarDiasFecha(fechaIso: string, dias: number): string {
  const fecha = new Date(fechaIso + 'T00:00:00Z')
  fecha.setUTCDate(fecha.getUTCDate() + dias)
  return fecha.toISOString().slice(0, 10)
}

export function diasHasta(fechaIso: string): number {
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  const fecha = new Date(fechaIso + 'T00:00:00')
  return Math.round((fecha.getTime() - hoy.getTime()) / 86_400_000)
}
