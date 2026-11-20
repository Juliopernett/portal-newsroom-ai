import { ChartPanel } from './ChartPanel'

export function ChartPage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold">Radar Vallenato</h1>
        <p className="text-sm text-muted-foreground">
          Edición semanal, imágenes para redes, canales y videos que alimentan el ranking.
        </p>
      </div>
      <ChartPanel />
    </div>
  )
}
