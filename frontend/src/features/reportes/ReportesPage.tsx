import { useMemo, useState } from 'react'
import { Download } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SelectNative } from '@/components/ui/select-native'
import { descargarArchivo } from '@/lib/descargar'

interface ReportOption {
  value: string
  label: string
  baseUrl: string
  helpText: string
}

const REPORTS: ReportOption[] = [
  {
    value: 'completo',
    label: 'Reporte completo',
    baseUrl: '/reportes/completo.xlsx',
    helpText:
      'Un solo archivo con cuatro pestañas: rentabilidad, pautas, gastos y otros ingresos. Vacío = histórico completo. Las pautas se filtran por fecha de inicio y la rentabilidad cuenta cada pauta por su fecha de pago.',
  },
  {
    value: 'rentabilidad',
    label: 'Rentabilidad mensual',
    baseUrl: '/reportes/rentabilidad.xlsx',
    helpText: 'Vacío = últimos 12 meses. Ingresos cobrados menos gastos registrados, por mes.',
  },
  {
    value: 'pautas',
    label: 'Pautas',
    baseUrl: '/reportes/pautas.xlsx',
    helpText: 'Vacío = histórico completo. Filtra por la fecha de inicio de cada pauta.',
  },
  {
    value: 'gastos',
    label: 'Gastos',
    baseUrl: '/reportes/gastos.xlsx',
    helpText: 'Vacío = histórico completo. Ordenado por fecha.',
  },
  {
    value: 'otros-ingresos',
    label: 'Otros ingresos',
    baseUrl: '/reportes/otros-ingresos.xlsx',
    helpText: 'Vacío = histórico completo. Ingresos recibidos fuera de una pauta (Facebook, AdSense…), ordenados por fecha de cobro.',
  },
]

export function ReportesPage() {
  const [selected, setSelected] = useState(REPORTS[0].value)
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')

  const report = REPORTS.find((r) => r.value === selected) ?? REPORTS[0]

  const href = useMemo(() => {
    const params = new URLSearchParams()
    if (desde) params.set('desde', desde)
    if (hasta) params.set('hasta', hasta)
    const query = params.toString()
    return query ? `${report.baseUrl}?${query}` : report.baseUrl
  }, [report.baseUrl, desde, hasta])

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold">Reportes</h1>
        <p className="text-sm text-muted-foreground">
          Descarga tus datos en Excel, con totales y filtros
        </p>
      </div>

      <div className="flex min-w-0 max-w-2xl flex-col gap-4 rounded-lg border border-border p-4">
        <div className="flex min-w-0 flex-col gap-2">
          <Label htmlFor="reporte-select">Reporte</Label>
          <SelectNative
            id="reporte-select"
            className="max-w-xs"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {REPORTS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </SelectNative>
        </div>

        {/* min-w-0 at every flex level here on purpose: Safari's native
            <input type=date> refuses to shrink below its own intrinsic
            content width unless every ancestor flex container explicitly
            overrides the default min-width:auto — otherwise the date
            field pushes this whole card wider than its border (confirmed
            on iPhone Safari; Chrome tolerates the same markup fine). */}
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
          <div className="flex min-w-0 w-full flex-col gap-2 sm:w-auto">
            <Label htmlFor="reporte-desde">Desde</Label>
            <Input
              id="reporte-desde"
              type="date"
              className="min-w-0 w-full"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
            />
          </div>
          <div className="flex min-w-0 w-full flex-col gap-2 sm:w-auto">
            <Label htmlFor="reporte-hasta">Hasta</Label>
            <Input
              id="reporte-hasta"
              type="date"
              className="min-w-0 w-full"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
            />
          </div>
          <Button
            variant="secondary"
            className="w-full sm:w-auto"
            onClick={() => void descargarArchivo(href, `${report.value}.xlsx`)}
          >
            <Download /> Descargar Excel
          </Button>
        </div>

        <p className="text-sm text-muted-foreground">{report.helpText}</p>
      </div>
    </div>
  )
}
