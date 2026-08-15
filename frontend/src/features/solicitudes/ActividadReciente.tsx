import type { Pauta } from '@/features/contratos/api'
import { formatHoras, horasEnEspera } from './utils'
import type { Solicitud } from './api'

const LIMITE = 25

interface Evento {
  fecha: string
  texto: string
}

export function ActividadReciente({
  pendientes,
  publicadas,
  pautas,
  clientesById,
}: {
  pendientes: Solicitud[]
  publicadas: Solicitud[]
  pautas: Pauta[]
  clientesById: Map<string, string>
}) {
  const pautasById = new Map(pautas.map((p) => [p.id, p]))
  const nombreDeSolicitud = (s: Solicitud) => {
    if (!s.pauta_id) return null
    const pauta = pautasById.get(s.pauta_id)
    return pauta ? (clientesById.get(pauta.client_id) ?? null) : null
  }

  const eventos: Evento[] = [
    ...publicadas.map((s) => ({
      fecha: s.fecha_recepcion,
      texto: `✅ Se publicó ${nombreDeSolicitud(s) ?? '(cliente desconocido)'}`,
    })),
    ...pendientes.map((s) => {
      const nombre = nombreDeSolicitud(s)
      return { fecha: s.fecha_recepcion, texto: `➕ Nueva solicitud${nombre ? ` de ${nombre}` : ''}` }
    }),
    ...pautas.map((p) => {
      const nombre = clientesById.get(p.client_id)
      return {
        fecha: p.fecha_registro || p.fecha_inicio,
        texto: `🟠 Pauta registrada${nombre ? ` — ${nombre}` : ''}`,
      }
    }),
  ]
    .sort((a, b) => b.fecha.localeCompare(a.fecha))
    .slice(0, LIMITE)

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-sm font-medium">
        <span className="size-2 animate-pulse rounded-full bg-success" />
        Actividad reciente
      </div>
      <aside className="rounded-lg border border-border bg-card p-3">
        {eventos.length === 0 ? (
          <p className="p-4 text-center text-sm text-muted-foreground">🕐 Sin actividad todavía.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {eventos.map((e, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className="w-20 shrink-0 text-muted-foreground">{formatHoras(horasEnEspera(e.fecha))}</span>
                <span className="h-4 w-px shrink-0 bg-border" />
                <span className="pl-1">{e.texto}</span>
              </div>
            ))}
          </div>
        )}
      </aside>
    </div>
  )
}
