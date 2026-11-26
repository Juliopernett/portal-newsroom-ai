import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

// Igual que MAX_CARACTERES_ANTETITULO en el backend: el gancho va siempre en una línea.
export const MAX_GANCHO = 35

export function CampoGancho({
  id,
  value,
  onChange,
}: {
  id: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={id}>Gancho (botón amarillo, opcional)</Label>
        <span aria-hidden className="text-xs tabular-nums text-muted-foreground">
          {value.length}/{MAX_GANCHO}
        </span>
      </div>
      <Input
        id={id}
        aria-describedby={`${id}-ayuda`}
        placeholder="Ej. ¡Confirmado!"
        maxLength={MAX_GANCHO}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <p id={`${id}-ayuda`} className="text-xs text-muted-foreground">
        Una sola línea, hasta {MAX_GANCHO} caracteres: va en un botón amarillo sobre el titular.
      </p>
    </div>
  )
}
