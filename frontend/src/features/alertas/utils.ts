import { useSyncExternalStore } from 'react'
import { diasHasta } from '@/lib/format'
import type { AlertaInteligente, AlertaSeveridad, DashboardAlertas, NivelSalud, RankingComercialItem } from './api'

// Same client + same message can legitimately appear more than once in
// Centro de Alertas (e.g. two separate solicitudes received within the
// last 24h both render "X ya envió material nuevo.") — grouped by this
// key wherever the list is counted or rendered, so the count and the
// grouped display never drift apart.
export function centroAlertaKey(item: AlertaInteligente): string {
  return `${item.cliente?.id ?? 'sin-cliente'}::${item.mensaje}`
}

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

// Client-only "descartar" (dismiss) for one-off alerts — the backend has
// no concept of acknowledged alerts, and adding one is out of scope here.
// A dismissed alert just stops rendering until the user restores it; if
// the underlying condition changes the API stops returning it anyway, so
// stale keys in storage are harmless, just unused.
const DISMISSED_STORAGE_KEY = 'pv-alertas-descartadas'

function readDismissed(): Set<string> {
  try {
    const raw = localStorage.getItem(DISMISSED_STORAGE_KEY)
    return new Set(raw ? (JSON.parse(raw) as string[]) : [])
  } catch {
    return new Set()
  }
}

// A tiny external store (not React state) so every component calling
// useDismissedAlerts() — AlertasPage's lists AND Shell's sidebar badge —
// shares one live value. Plain per-component useState would desync them:
// dismissing on the page wouldn't update the badge until a full remount.
let dismissedSnapshot: Set<string> = readDismissed()
const listeners = new Set<() => void>()

function persist(next: Set<string>) {
  dismissedSnapshot = next
  try {
    localStorage.setItem(DISMISSED_STORAGE_KEY, JSON.stringify([...next]))
  } catch {
    // localStorage unavailable (e.g. private mode) — dismiss just won't persist across reloads
  }
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useDismissedAlerts() {
  const dismissed = useSyncExternalStore(subscribe, () => dismissedSnapshot)

  return {
    isDismissed: (key: string) => dismissed.has(key),
    dismiss: (key: string) => persist(new Set(dismissed).add(key)),
    dismissedCount: dismissed.size,
    restoreAll: () => persist(new Set()),
  }
}

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
