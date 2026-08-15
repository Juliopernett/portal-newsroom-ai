// Purely visual — distinct from EstadoComercial (backend-computed,
// see core/analytics/view_models.py), which is about renewal urgency,
// not raw quota level. Both are shown on client-facing cards but they
// answer different questions.
export function cupoNivel(restantes: number, contratadas: number, vigente: boolean): string {
  if (!vigente) return 'vencido'
  if (restantes <= 0) return 'agotado'
  const pct = contratadas > 0 ? restantes / contratadas : 0
  if (pct > 0.4) return 'alto'
  if (pct >= 0.15) return 'medio'
  return 'bajo'
}

export const CUPO_BAR_COLOR: Record<string, string> = {
  vencido: 'bg-muted-foreground',
  agotado: 'bg-danger',
  bajo: 'bg-warning',
  medio: 'bg-warning',
  alto: 'bg-success',
}
