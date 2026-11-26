import { useEffect, useState } from 'react'

import { Label } from '@/components/ui/label'
import { ENCUADRE_INICIAL, type Encuadre } from './api'

// Ancho / alto de la foto elegida (null mientras se lee o si no se puede leer).
function useProporcion(imagen: File | null) {
  const [leida, setLeida] = useState<{ imagen: File; proporcion: number } | null>(null)
  useEffect(() => {
    if (!imagen) return
    let vigente = true
    createImageBitmap(imagen)
      .then((foto) => {
        if (vigente) setLeida({ imagen, proporcion: foto.width / foto.height })
        foto.close()
      })
      .catch(() => {})
    return () => {
      vigente = false
    }
  }, [imagen])
  return leida && leida.imagen === imagen ? leida.proporcion : null
}

export function ControlesEncuadre({
  idBase,
  imagen,
  value,
  onChange,
  onSoltar,
}: {
  idBase: string
  imagen: File | null
  value: Encuadre
  onChange: (value: Encuadre) => void
  // Se llama al soltar un control: sirve para refrescar la vista previa.
  onSoltar?: () => void
}) {
  const proporcion = useProporcion(imagen)
  // Sin acercar, la foto solo se mueve por el lado que sobra frente al 4:5.
  const sinAcercar = value.zoom <= ENCUADRE_INICIAL.zoom
  const sinMargenX = sinAcercar && proporcion !== null && proporcion <= 0.805
  const sinMargenY = sinAcercar && proporcion !== null && proporcion >= 0.795

  const control = (
    id: string,
    etiqueta: string,
    ayuda: string,
    campo: keyof Encuadre,
    min: number,
    max: number,
    bloqueado = false,
  ) => (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={`${id}-${idBase}`}>{etiqueta}</Label>
      <input
        id={`${id}-${idBase}`}
        type="range"
        min={min}
        max={max}
        step={1}
        disabled={bloqueado}
        className="disabled:opacity-40"
        value={Math.round(value[campo] * 100)}
        onChange={(e) => onChange({ ...value, [campo]: Number(e.target.value) / 100 })}
        onPointerUp={onSoltar}
        onKeyUp={onSoltar}
      />
      <span className="text-xs text-muted-foreground">
        {bloqueado ? 'Acerca la foto para moverla' : ayuda}
      </span>
    </div>
  )

  return (
    <div className="flex flex-col gap-3">
      {control(
        'encuadre-zoom',
        `Acercar foto (${Math.round(value.zoom * 100)}%)`,
        '100% = sin acercar',
        'zoom',
        100,
        250,
      )}
      <div className="grid grid-cols-2 gap-3">
        {control(
          'encuadre-y',
          'Encuadre vertical',
          'Arriba ↔ abajo',
          'enfoqueY',
          0,
          100,
          sinMargenY,
        )}
        {control(
          'encuadre-x',
          'Encuadre horizontal',
          'Izquierda ↔ derecha',
          'enfoqueX',
          0,
          100,
          sinMargenX,
        )}
      </div>
    </div>
  )
}
