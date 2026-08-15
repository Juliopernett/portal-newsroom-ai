import { formatMoneda } from '@/lib/format'
import type { Pauta } from '@/features/contratos/api'
import type {
  CanalPublicacion,
  EstadoDestino,
  MediaAssetTipo,
  ReporteSolicitud,
  Solicitud,
} from './api'

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

export { STALE_REQUEST_HOURS }

// ---------- Destinos (multi-canal) ----------

export const CANALES_DESTINO: { value: CanalPublicacion; label: string }[] = [
  { value: 'wordpress', label: 'WordPress' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'instagram', label: 'Instagram' },
]

export const DESTINO_ESTADO_LABELS: Record<EstadoDestino, string> = {
  pendiente: 'Pendiente',
  publicado: 'Publicado',
  fallido: 'Falló',
  cancelado: 'Cancelado',
}

export const DESTINO_ESTADO_BADGE: Record<EstadoDestino, string> = {
  pendiente: 'bg-muted text-muted-foreground',
  publicado: 'bg-success-bg text-success',
  fallido: 'bg-danger-bg text-danger',
  cancelado: 'bg-muted text-muted-foreground',
}

// ---------- Media ----------

export const MEDIA_TIPO_LABELS: Record<MediaAssetTipo, string> = {
  imagen: 'Imagen',
  video: 'Video',
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ---------- Reporte ----------

export function formatoReporteTexto(reporte: ReporteSolicitud): string {
  const lineas = [
    reporte.titulo ? `Reporte: ${reporte.titulo}` : 'Reporte de publicación',
    `Cliente: ${reporte.cliente_nombre ?? '(sin vincular)'}`,
    `Estado: ${reporte.completa ? 'Completa' : 'En curso'}`,
    `Pauta consumida: ${reporte.pauta_consumida ? 'Sí' : 'No'}`,
    '',
    'Destinos:',
  ]
  if (reporte.destinos.length === 0) {
    lineas.push('  (sin destinos todavía)')
  } else {
    for (const d of reporte.destinos) {
      const canalLabel = CANALES_DESTINO.find((c) => c.value === d.canal)?.label ?? d.canal
      const estadoLabel = DESTINO_ESTADO_LABELS[d.estado]
      let linea = `  - ${canalLabel}: ${estadoLabel}`
      if (d.enlace) linea += ` — ${d.enlace}`
      if (d.fecha_publicacion) linea += ` (${d.fecha_publicacion.slice(0, 10)})`
      lineas.push(linea)
    }
  }
  return lineas.join('\n')
}
