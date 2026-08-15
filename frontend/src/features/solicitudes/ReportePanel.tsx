import { useQuery } from '@tanstack/react-query'
import { Copy } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { solicitudesApi } from './api'
import { CANALES_DESTINO, DESTINO_ESTADO_BADGE, DESTINO_ESTADO_LABELS, formatoReporteTexto } from './utils'

export function ReportePanel({ solicitudId }: { solicitudId: string }) {
  const reporteQuery = useQuery({
    queryKey: ['reporte', solicitudId],
    queryFn: () => solicitudesApi.getReporte(solicitudId),
  })

  async function copiar() {
    if (!reporteQuery.data) return
    try {
      await navigator.clipboard.writeText(formatoReporteTexto(reporteQuery.data))
      toast.success('Reporte copiado al portapapeles.')
    } catch {
      toast.error('No se pudo copiar el reporte. Copia el texto a mano.')
    }
  }

  if (reporteQuery.isLoading) {
    return <p className="rounded-md border border-border bg-background p-3 text-sm text-muted-foreground">Cargando…</p>
  }
  const reporte = reporteQuery.data
  if (!reporte) return null

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-background p-3 text-sm">
      <p>
        <span className="text-muted-foreground">Cliente:</span> {reporte.cliente_nombre ?? '(sin vincular)'}
      </p>
      <p>
        <span className="text-muted-foreground">Pauta consumida:</span> {reporte.pauta_consumida ? 'Sí' : 'No'}
      </p>
      {reporte.destinos.length === 0 ? (
        <p className="text-muted-foreground">Sin destinos todavía.</p>
      ) : (
        <div className="flex flex-col divide-y divide-border">
          {reporte.destinos.map((d, i) => {
            const canalLabel = CANALES_DESTINO.find((c) => c.value === d.canal)?.label ?? d.canal
            return (
              <div key={i} className="flex items-center justify-between gap-2 py-1.5">
                <div className="flex items-center gap-2">
                  <span>{canalLabel}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${DESTINO_ESTADO_BADGE[d.estado]}`}>
                    {DESTINO_ESTADO_LABELS[d.estado]}
                  </span>
                </div>
                {d.enlace ? (
                  <a className="text-xs text-brand underline" href={d.enlace} target="_blank" rel="noopener">
                    Ver publicación
                  </a>
                ) : (
                  <span className="text-xs text-muted-foreground">Sin enlace todavía</span>
                )}
              </div>
            )
          })}
        </div>
      )}
      <Button variant="secondary" size="sm" className="self-start" onClick={copiar}>
        <Copy /> Copiar reporte
      </Button>
    </div>
  )
}
