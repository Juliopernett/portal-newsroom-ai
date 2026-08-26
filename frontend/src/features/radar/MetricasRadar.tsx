import { Bookmark, Sparkles, Telescope, Trash2 } from 'lucide-react'

import { fechaNegocioISO } from '@/lib/format'
import type { NewsCandidate } from './api'

function StatTile({ icon: Icon, valor, label }: { icon: typeof Sparkles; valor: number; label: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-card p-3">
      <Icon className="size-4 text-muted-foreground" />
      <span className="text-lg font-semibold">{valor}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
}

export function MetricasRadar({ candidatos }: { candidatos: NewsCandidate[] }) {
  const nuevas = candidatos.filter((c) => c.estado === 'nuevo').length
  const guardadas = candidatos.filter((c) => c.estado === 'guardado').length
  const descartadas = candidatos.filter((c) => c.estado === 'descartado').length
  const hoyStr = fechaNegocioISO()
  const descubiertasHoy = candidatos.filter((c) => fechaNegocioISO(c.discovered_at) === hoyStr).length

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      <StatTile icon={Sparkles} valor={nuevas} label="Nuevas" />
      <StatTile icon={Bookmark} valor={guardadas} label="Guardadas" />
      <StatTile icon={Trash2} valor={descartadas} label="Descartadas" />
      <StatTile icon={Telescope} valor={descubiertasHoy} label="Descubiertas hoy" />
    </div>
  )
}
