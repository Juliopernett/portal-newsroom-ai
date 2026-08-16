import { useMemo, useState } from 'react'
import { Download } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SelectNative } from '@/components/ui/select-native'

interface ReportOption {
  value: string
  label: string
  baseUrl: string
  helpText: string
}

const REPORTS: ReportOption[] = [
  {
    value: 'rentabilidad',
    label: 'Rentabilidad mensual',
    baseUrl: '/reportes/rentabilidad.csv',
    helpText: 'Vacío = últimos 12 meses. Ingresos cobrados menos gastos registrados, por mes.',
  },
  {
    value: 'pautas',
    label: 'Pautas',
    baseUrl: '/reportes/pautas.csv',
    helpText: 'Vacío = histórico completo. Filtra por la fecha de inicio de cada pauta.',
  },
  {
    value: 'gastos',
    label: 'Gastos',
    baseUrl: '/reportes/gastos.csv',
    helpText: 'Vacío = histórico completo. Ordenado por fecha.',
  },
  {
    value: 'otros-ingresos',
    label: 'Otros ingresos',
    baseUrl: '/reportes/otros-ingresos.csv',
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
          Exporta CSV para abrir en Excel — deja las fechas vacías para el histórico completo
        </p>
      </div>

      <div className="flex max-w-2xl flex-col gap-4 rounded-lg border border-border p-4">
        <div className="flex flex-col gap-2">
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

        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-2">
            <Label htmlFor="reporte-desde">Desde</Label>
            <Input
              id="reporte-desde"
              type="date"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="reporte-hasta">Hasta</Label>
            <Input
              id="reporte-hasta"
              type="date"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
            />
          </div>
          <Button variant="secondary" asChild>
            <a href={href} target="_blank" rel="noopener">
              <Download /> Descargar CSV
            </a>
          </Button>
        </div>

        <p className="text-sm text-muted-foreground">{report.helpText}</p>
      </div>
    </div>
  )
}
