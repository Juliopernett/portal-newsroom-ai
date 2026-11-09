import { useMutation } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { insightsApi } from './api'

const PRIORIDAD_ESTILO: Record<string, string> = {
  alta: 'bg-danger-bg text-danger',
  media: 'bg-warning-bg text-warning',
  baja: 'bg-muted text-muted-foreground',
}

// Solo lectura: la IA lee los números del negocio y sugiere; tú decides.
export function AsesorIA() {
  const analizar = useMutation({
    mutationFn: insightsApi.asesor,
    onError: (err) => toast.error(errorMessage(err)),
  })
  const data = analizar.data

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Asesor IA</h2>
          <p className="text-sm text-muted-foreground">
            Lee tus contratos, ingresos, gastos y clientes, y te sugiere qué mejorar. Solo
            aconseja: no cambia nada ni escribe a nadie.
          </p>
        </div>
        <Button onClick={() => analizar.mutate()} disabled={analizar.isPending}>
          <Sparkles className={analizar.isPending ? 'animate-pulse' : ''} />
          {analizar.isPending ? 'Analizando…' : data ? 'Analizar de nuevo' : 'Analizar mi negocio'}
        </Button>
      </div>

      {data && (
        <div className="flex flex-col gap-3">
          <p className="rounded-md bg-muted/50 p-3 text-sm">{data.resumen}</p>
          <ul className="flex flex-col gap-2">
            {data.sugerencias.map((s) => (
              <li key={s.titulo} className="rounded-lg border border-border p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${PRIORIDAD_ESTILO[s.prioridad] ?? ''}`}
                  >
                    {s.prioridad}
                  </span>
                  <span className="text-xs text-muted-foreground">{s.area}</span>
                  {s.cliente && <span className="text-xs font-medium">· {s.cliente}</span>}
                </div>
                <p className="mt-1 font-medium">{s.titulo}</p>
                <p className="text-muted-foreground">{s.detalle}</p>
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">
            Sugerencias de una IA a partir de tus datos: verifícalas antes de actuar.
          </p>
        </div>
      )}
    </section>
  )
}
