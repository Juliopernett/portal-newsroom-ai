import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Download, ImagePlus, Loader2, Sparkles } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { guardarBlob } from '@/lib/descargar'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SelectNative } from '@/components/ui/select-native'
import { ENCUADRE_INICIAL, portadasApi, type VariantePortada } from './api'
import { CampoGancho } from './CampoGancho'
import { ControlesEncuadre } from './ControlesEncuadre'

export function PortadasPage() {
  const [imagenBase, setImagenBase] = useState<File | null>(null)
  const [imagenCirculo, setImagenCirculo] = useState<File | null>(null)
  const [titular, setTitular] = useState('')
  const [antetitulo, setAntetitulo] = useState('')
  const [variante, setVariante] = useState<VariantePortada>('noticias')
  const [encuadre, setEncuadre] = useState(ENCUADRE_INICIAL)
  const [vistaPrevia, setVistaPrevia] = useState<string | null>(null)

  // Libera la URL del blob anterior al reemplazarla o al salir de la página.
  useEffect(() => {
    return () => {
      if (vistaPrevia) URL.revokeObjectURL(vistaPrevia)
    }
  }, [vistaPrevia])

  const generarMutation = useMutation({
    mutationFn: () =>
      portadasApi.generar({
        imagenBase: imagenBase as File,
        imagenCirculo,
        titular,
        antetitulo,
        variante,
        ...encuadre,
      }),
  })

  const puedeGenerar = imagenBase !== null && titular.trim().length > 0

  // Los callbacks de `mutate` solo corren para la petición más reciente.
  const generar = () =>
    generarMutation.mutate(undefined, {
      onSuccess: (blob) => setVistaPrevia(URL.createObjectURL(blob)),
      onError: (err) => toast.error(errorMessage(err)),
    })

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold">Portadas</h1>
        <p className="text-sm text-muted-foreground">
          Arma la portada 4:5 con la plantilla de Portal Vallenato — la misma imagen sirve para
          WordPress y para redes.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,26rem)_1fr]">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="portada-variante">Plantilla</Label>
            <SelectNative
              id="portada-variante"
              value={variante}
              onChange={(e) => setVariante(e.target.value as VariantePortada)}
            >
              <option value="noticias">Noticias</option>
              <option value="lo_ultimo">Lo último (noticia de último momento)</option>
            </SelectNative>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="portada-base">Imagen base</Label>
            <Input
              id="portada-base"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => {
                setImagenBase(e.target.files?.[0] ?? null)
                setEncuadre(ENCUADRE_INICIAL)
              }}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="portada-circulo">Segunda foto en círculo (opcional)</Label>
            <Input
              id="portada-circulo"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setImagenCirculo(e.target.files?.[0] ?? null)}
            />
            <p className="text-xs text-muted-foreground">
              Si la agregas, se usa la plantilla con círculo y flecha para llamar la atención.
            </p>
          </div>

          <CampoGancho
            id="portada-antetitulo"
            value={antetitulo}
            onChange={setAntetitulo}
          />

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="portada-titular">Titular</Label>
            <Input
              id="portada-titular"
              placeholder="Rafa Pérez tendrá ocho presentaciones este fin de semana"
              maxLength={200}
              value={titular}
              onChange={(e) => setTitular(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Se escribe en mayúsculas automáticamente y el tamaño se ajusta solo.
            </p>
          </div>

          <ControlesEncuadre
            idBase="portadas"
            imagen={imagenBase}
            value={encuadre}
            onChange={setEncuadre}
            // Con una vista previa a la vista, se actualiza sola al soltar un control.
            onSoltar={vistaPrevia && puedeGenerar ? generar : undefined}
          />

          <Button
            disabled={!puedeGenerar || generarMutation.isPending}
            onClick={generar}
          >
            {generarMutation.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
            Generar portada
          </Button>
        </div>

        <div className="flex flex-col items-start gap-3">
          {vistaPrevia ? (
            <>
              <img
                src={vistaPrevia}
                alt="Vista previa de la portada"
                className="w-full max-w-md rounded-lg border border-border"
              />
              <Button
                variant="outline"
                onClick={async () =>
                  guardarBlob(await (await fetch(vistaPrevia)).blob(), 'portada.png')
                }
              >
                <Download /> Descargar PNG
              </Button>
            </>
          ) : (
            <div className="flex aspect-[4/5] w-full max-w-md flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border text-sm text-muted-foreground">
              <ImagePlus className="size-8" />
              La vista previa aparece aquí
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
