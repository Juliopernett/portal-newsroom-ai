import { diasHasta } from '@/lib/format'
import type { AlertaSeveridad, DashboardAlertas, NivelSalud, RankingComercialItem } from './api'

export const SEVERIDAD_EMOJI: Record<AlertaSeveridad, string> = {
  critica: '🔴',
  atencion: '🟠',
  informativa: '🟢',
}

export const SEVERIDAD_BORDER: Record<AlertaSeveridad, string> = {
  critica: 'border-l-danger',
  atencion: 'border-l-warning',
  informativa: 'border-l-success',
}

export const NIVEL_SALUD_LABELS: Record<NivelSalud, string> = {
  excelente: 'Cliente saludable',
  bueno: 'Sin riesgo inminente',
  regular: 'Atención recomendada',
  riesgo: 'Riesgo de perder renovación',
  critico: 'Riesgo alto — contactar ya',
}

export const NIVEL_SALUD_BADGE: Record<NivelSalud, string> = {
  excelente: 'bg-success-bg text-success',
  bueno: 'bg-success-bg text-success',
  regular: 'bg-muted text-muted-foreground',
  riesgo: 'bg-warning-bg text-warning',
  critico: 'bg-danger-bg text-danger',
}

export function renderEstrellas(n: number): string {
  return '★'.repeat(n) + '☆'.repeat(5 - n)
}

// wa.me requires a bare digit string — no spaces/dashes/parens. An
// optional prefilled message is just a `text` query param — the
// recipient can still edit it before sending, never sent automatically.
export function waLink(telefono: string, mensaje?: string): string | null {
  const digits = telefono.replace(/\D/g, '')
  if (!digits) return null
  const base = `https://wa.me/${digits}`
  return mensaje ? `${base}?text=${encodeURIComponent(mensaje)}` : base
}

type CampoClientes = Exclude<keyof DashboardAlertas, 'solicitudes_antiguas'>

interface OportunidadCategoria {
  id: string
  campo: CampoClientes
  label: string
  tone: 'neutral' | 'success'
}

// The 4 "general" categories that predate the fine-grained
// pattern-based ones (which come from /insights/oportunidades instead).
export const ALERTAS_OPORTUNIDAD: OportunidadCategoria[] = [
  { id: 'individuales', campo: 'clientes_individuales_pendientes', tone: 'neutral', label: 'publicaciones individuales pendientes' },
  { id: 'renovar', campo: 'clientes_contrato_por_renovar', tone: 'neutral', label: 'contratos próximos a renovar' },
  { id: 'sin-usar', campo: 'clientes_publicaciones_sin_usar', tone: 'neutral', label: 'dejaron publicaciones sin usar' },
  { id: 'premium', campo: 'clientes_premium', tone: 'success', label: 'clientes premium (semestral/anual)' },
]

export interface RenewalBucket {
  titulo: string
  emoji: string
  items: { item: RankingComercialItem; dias: number }[]
}

const RENEWAL_BUCKET_LIMITS = [
  { limite: 7, titulo: 'Vence en 7 días', emoji: '🔴' },
  { limite: 15, titulo: 'Vence en 15 días', emoji: '🟠' },
  { limite: 30, titulo: 'Vence en 30 días', emoji: '🟢' },
]

// Only vigente clients with a time package (not Individual — those don't
// "renew"), grouped by how close their vencimiento is. Never shows
// expired ones. Same partition feeds both the summary counts and the
// detailed cards, so they can never drift apart.
export function computarRadarBuckets(ranking: RankingComercialItem[]): RenewalBucket[] {
  const candidatos = ranking
    .filter((item) => item.vigente && item.tipo !== 'individual')
    .map((item) => ({ item, dias: diasHasta(item.fecha_vencimiento) }))
    .filter(({ dias }) => dias >= 0 && dias <= 30)
    .sort((a, b) => a.dias - b.dias)

  let restantes = candidatos
  return RENEWAL_BUCKET_LIMITS.map(({ limite, titulo, emoji }) => {
    const items = restantes.filter(({ dias }) => dias <= limite)
    restantes = restantes.filter(({ dias }) => dias > limite)
    return { titulo, emoji, items }
  })
}
