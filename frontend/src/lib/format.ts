export function formatMoneda(valor: string | number): string {
  return '$' + Number(valor).toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

export function formatFecha(iso: string): string {
  return iso ? iso.slice(0, 10) : ''
}

const NEGOCIO_TZ = 'America/Bogota'

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
