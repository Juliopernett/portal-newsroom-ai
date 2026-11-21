import { useQuery } from '@tanstack/react-query'
import { Copy } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ContactarButton, VerClienteButton } from '@/features/alertas/components'
import { CLIENT_TYPE_LABELS } from '@/features/clientes/api'
import { PAUTA_TIPO_LABELS } from '@/features/contratos/api'
import { formatFecha, formatMoneda } from '@/lib/format'
import { deudoresApi, type Deudor } from './api'

// Mismo tono que el mensaje de cobro de Alertas; solo agrega el detalle por plan cuando
// el cliente debe en más de uno. Nunca se envía solo: se copia o se abre en WhatsApp.
function mensajeCobro(d: Deudor): string {
  const total = formatMoneda(d.total_pendiente)
  const detalle =
    d.saldos.length === 1
      ? ` de tu plan ${PAUTA_TIPO_LABELS[d.saldos[0].tipo]}`
      : ` (${d.saldos.map((s) => `${PAUTA_TIPO_LABELS[s.tipo]}: ${formatMoneda(s.saldo_pendiente)}`).join(', ')})`
  return `Hola ${d.cliente.nombre}, te escribimos de Portal Vallenato — tienes un saldo pendiente de ${total}${detalle}. ¿Puedes completar el pago? ¡Gracias!`
}

async function copiarMensaje(d: Deudor) {
  try {
    await navigator.clipboard.writeText(mensajeCobro(d))
    toast.success(`Mensaje de cobro para ${d.cliente.nombre} copiado.`)
  } catch {
    toast.error('No se pudo copiar — abre WhatsApp con el botón Contactar.')
  }
}

function Antiguedad({ dias }: { dias: number }) {
  const estilo =
    dias > 60
      ? 'bg-danger-bg text-danger'
      : dias > 30
        ? 'bg-warning-bg text-warning'
        : 'bg-muted text-muted-foreground'
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${estilo}`}>
      {dias === 0 ? 'Pagó hoy' : `Sin completar hace ${dias} días`}
    </span>
  )
}

export function DeudoresPage() {
  const query = useQuery({ queryKey: ['deudores'], queryFn: deudoresApi.list })
  const data = query.data

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold">Deudores</h1>
        <p className="text-sm text-muted-foreground">
          Clientes que pagaron una parte y todavía te deben el resto. Se arma solo con el saldo
          pendiente de cada contrato; para registrar un pago, edita el saldo en Contratos.
        </p>
      </div>

      {query.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : query.isError ? (
        <p role="alert" className="rounded-md bg-danger-bg px-3 py-2 text-sm text-danger">
          No se pudo cargar la lista de deudores.{' '}
          <button type="button" className="underline" onClick={() => query.refetch()}>
            Reintentar
          </button>
        </p>
      ) : !data || data.deudores.length === 0 ? (
        <p className="rounded-lg border border-border bg-card px-4 py-6 text-center text-sm text-muted-foreground">
          ✅ Nadie te debe por ahora: no hay saldos pendientes.
        </p>
      ) : (
        <>
          <div className="grid max-w-xl grid-cols-2 gap-3">
            <Card className="gap-1 px-4 py-3">
              <p className="text-xs text-muted-foreground">Total por cobrar</p>
              <p className="text-xl font-semibold">{formatMoneda(data.total_por_cobrar)}</p>
            </Card>
            <Card className="gap-1 px-4 py-3">
              <p className="text-xs text-muted-foreground">Clientes con deuda</p>
              <p className="text-xl font-semibold">{data.cantidad}</p>
            </Card>
          </div>

          <ul className="flex flex-col gap-3">
            {data.deudores.map((d) => (
              <li key={d.cliente.id}>
                <Card className="gap-3 px-4 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-medium">{d.cliente.nombre}</p>
                      <p className="text-xs text-muted-foreground">
                        {CLIENT_TYPE_LABELS[d.cliente.tipo]} · {d.cliente.telefono}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <p className="text-lg font-semibold">{formatMoneda(d.total_pendiente)}</p>
                      <Antiguedad dias={d.dias_mas_antiguo} />
                    </div>
                  </div>

                  <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
                    {d.saldos.map((s) => (
                      <li key={s.pauta_id}>
                        Plan {PAUTA_TIPO_LABELS[s.tipo]} · pagó el {formatFecha(s.fecha_pago)} · termina el{' '}
                        {formatFecha(s.fecha_fin)}
                        {s.vencida ? ' (ya venció)' : ''} ·{' '}
                        <span className="font-medium text-foreground">
                          debe {formatMoneda(s.saldo_pendiente)}
                        </span>
                      </li>
                    ))}
                  </ul>

                  <div className="flex flex-wrap gap-2">
                    <ContactarButton telefono={d.cliente.telefono} mensaje={mensajeCobro(d)} />
                    <Button size="sm" variant="secondary" onClick={() => copiarMensaje(d)}>
                      <Copy /> Copiar mensaje
                    </Button>
                    <VerClienteButton clienteId={d.cliente.id} />
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
