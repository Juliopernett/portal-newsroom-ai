import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

// Texto alternativo de la imagen destacada en WordPress (guía del W3C): una frase corta
// sobre lo que aporta la foto, sin repetir el titular. Si la imagen es un afiche, el
// texto importante que trae escrito.
export function CampoDescripcionFoto({
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
      <Label htmlFor={id}>Descripción de la foto (texto alternativo)</Label>
      <Input
        id={id}
        aria-describedby={`${id}-ayuda`}
        placeholder="Ej. Silvestre Dangond cantando en tarima"
        maxLength={300}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <p id={`${id}-ayuda`} className="text-xs text-muted-foreground">
        Di en una frase corta qué se ve, sin repetir el titular. Si es un afiche, escribe sus datos
        (evento, fecha, lugar). Vacío = se usa el titular de la nota.
      </p>
    </div>
  )
}
