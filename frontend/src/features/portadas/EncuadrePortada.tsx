import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Eye, Loader2 } from 'lucide-react'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { portadasApi, type Encuadre, type GenerarPortadaInput } from './api'
import { ControlesEncuadre } from './ControlesEncuadre'

// Encuadre + vista previa para los diálogos que crean borradores (Radar y Solicitudes).
export function EncuadrePortada({
  idBase,
  portada,
  onChange,
}: {
  idBase: string
  portada: GenerarPortadaInput
  onChange: (encuadre: Encuadre) => void
}) {
  const [vistaPrevia, setVistaPrevia] = useState<string | null>(null)
  const previa = useMutation({ mutationFn: portadasApi.generar })

  useEffect(() => {
    return () => {
      if (vistaPrevia) URL.revokeObjectURL(vistaPrevia)
    }
  }, [vistaPrevia])

  function generar() {
    const titular = portada.titular.trim() || 'Aquí va el titular que redacte la IA'
    // Los callbacks de `mutate` solo corren para la petición más reciente.
    previa.mutate(
      { ...portada, titular },
      { onSuccess: (blob) => setVistaPrevia(URL.createObjectURL(blob)) },
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <ControlesEncuadre
        idBase={idBase}
        imagen={portada.imagenBase}
        value={portada}
        onChange={({ enfoqueX, enfoqueY, zoom }) => onChange({ enfoqueX, enfoqueY, zoom })}
        onSoltar={vistaPrevia ? generar : undefined}
      />
      <Button type="button" size="sm" variant="outline" onClick={generar}>
        {previa.isPending ? <Loader2 className="animate-spin" /> : <Eye />}
        {vistaPrevia ? 'Actualizar vista previa' : 'Ver vista previa de la portada'}
      </Button>
      {previa.isError && (
        <p role="alert" className="text-sm text-destructive">
          No se pudo generar la vista previa: {errorMessage(previa.error)}
        </p>
      )}
      {vistaPrevia && (
        <img
          src={vistaPrevia}
          alt="Vista previa de la portada"
          className="mx-auto w-full max-w-64 rounded-lg border border-border"
        />
      )}
    </div>
  )
}
