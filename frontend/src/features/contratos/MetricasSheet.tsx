import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { formatFecha } from '@/lib/format'
import { pautasApi, type FilaMetrica, type MetricasPauta, type Pauta } from './api'

const CANAL_LABEL = { facebook: 'Facebook', instagram: 'Instagram' } as const

// "—" means Meta did not report the number — never shown as 0.
function num(valor: number | null | undefined): string {
  return valor == null ? '—' : valor.toLocaleString('es-CO')
}

function Cifra({ label, valor }: { label: string; valor: number | null }) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{num(valor)}</p>
    </div>
  )
}

function FilaPublicacion({ fila }: { fila: FilaMetrica }) {
  const m = fila.metricas
  return (
    <li className="rounded-lg border border-border p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 font-medium break-words">{fila.titulo}</p>
        <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
          {CANAL_LABEL[fila.canal]}
        </span>
      </div>
      {m ? (
        <dl className="mt-2 grid grid-cols-3 gap-2 text-center">
          <div>
            <dt className="text-xs text-muted-foreground">Alcance</dt>
            <dd className="font-semibold">{num(m.alcance)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Visualiz.</dt>
            <dd className="font-semibold">{num(m.vistas)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Interacc.</dt>
            <dd className="font-semibold">{num(m.interacciones)}</dd>
          </div>
        </dl>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">
          {fila.tiene_meta_post_id
            ? 'Aún sin datos: pulsa «Actualizar desde Meta».'
            : 'Sin datos: el enlace se pegó a mano. Corrige el enlace eligiendo la publicación de la lista para poder medirla.'}
        </p>
      )}
    </li>
  )
}

export function MetricasSheet({ pauta, onClose }: { pauta: Pauta | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const key = ['pauta-metricas', pauta?.id]

  const query = useQuery({
    queryKey: key,
    queryFn: () => pautasApi.metricas(pauta!.id),
    enabled: pauta !== null,
  })

  const actualizar = useMutation({
    mutationFn: () => pautasApi.actualizarMetricas(pauta!.id),
    onSuccess: (data: MetricasPauta) => {
      queryClient.setQueryData(key, data)
      if (data.errores.length > 0) {
        toast.warning(`${data.errores.length} publicación(es) no se pudieron consultar.`)
      } else {
        toast.success('Métricas actualizadas.')
      }
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const data = query.data
  const ultima = data?.filas
    .map((f) => f.capturado_en)
    .filter((v): v is string => v !== null)
    .sort()
    .at(-1)

  return (
    <Sheet open={pauta !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="max-w-md overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Métricas de redes</SheetTitle>
          <SheetDescription>
            Vista interna: esto es lo que vería el cliente si el contrato incluye métricas.
          </SheetDescription>
        </SheetHeader>

        {query.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : query.isError || !data ? (
          <p className="text-sm text-danger">No se pudieron cargar las métricas.</p>
        ) : (
          <div className="flex flex-col gap-4">
            <p
              className={`rounded-md px-3 py-2 text-sm ${
                data.incluye_metricas
                  ? 'bg-success-bg text-success'
                  : 'bg-warning-bg text-warning'
              }`}
            >
              {data.incluye_metricas
                ? 'El informe de este cliente SÍ muestra estas métricas.'
                : 'El informe de este cliente NO muestra métricas (actívalo en «Editar»).'}
            </p>

            <div className="grid grid-cols-3 gap-2">
              <Cifra label="Alcance" valor={data.resumen.alcance_total} />
              <Cifra label="Visualiz." valor={data.resumen.vistas_total} />
              <Cifra label="Interacc." valor={data.resumen.interacciones_total} />
            </div>
            <p className="text-xs text-muted-foreground">
              {data.resumen.publicaciones_con_datos} de {data.resumen.publicaciones_total}{' '}
              publicaciones con datos
              {ultima ? ` · última captura ${formatFecha(ultima)}` : ''}
            </p>

            <Button onClick={() => actualizar.mutate()} disabled={actualizar.isPending}>
              <RefreshCw className={actualizar.isPending ? 'animate-spin' : ''} />
              {actualizar.isPending ? 'Consultando Meta…' : 'Actualizar desde Meta'}
            </Button>

            {data.errores.length > 0 && (
              <ul className="list-disc pl-5 text-xs text-danger">
                {data.errores.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            )}

            {data.filas.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Este contrato aún no tiene publicaciones en Facebook o Instagram.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {data.filas.map((fila) => (
                  <FilaPublicacion key={fila.destino_id} fila={fila} />
                ))}
              </ul>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
