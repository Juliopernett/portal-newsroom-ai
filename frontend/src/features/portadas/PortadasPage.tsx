import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Download, ImagePlus, Loader2, Sparkles } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SelectNative } from '@/components/ui/select-native'
import { portadasApi, type VariantePortada } from './api'

export function PortadasPage() {
  const [imagenBase, setImagenBase] = useState<File | null>(null)
  const [imagenCirculo, setImagenCirculo] = useState<File | null>(null)
  const [titular, setTitular] = useState('')
  const [antetitulo, setAntetitulo] = useState('')
  const [variante, setVariante] = useState<VariantePortada>('noticias')
  const [enfoqueY, setEnfoqueY] = useState(30)
  const [enfoqueX, setEnfoqueX] = useState(50)
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
        enfoqueX: enfoqueX / 100,
        enfoqueY: enfoqueY / 100,
      }),
    onSuccess: (blob) => setVistaPrevia(URL.createObjectURL(blob)),
    onError: (err) => toast.error(errorMessage(err)),
  })

  const puedeGenerar = imagenBase !== null && titular.trim().length > 0

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
              onChange={(e) => setImagenBase(e.target.files?.[0] ?? null)}
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

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="portada-antetitulo">Antetítulo (opcional)</Label>
            <Input
              id="portada-antetitulo"
              placeholder="¡CONFIRMADO!"
              maxLength={60}
              value={antetitulo}
              onChange={(e) => setAntetitulo(e.target.value)}
            />
          </div>

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

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="portada-enfoque-y">Encuadre vertical</Label>
              <input
                id="portada-enfoque-y"
                type="range"
                min={0}
                max={100}
                value={enfoqueY}
                onChange={(e) => setEnfoqueY(Number(e.target.value))}
              />
              <span className="text-xs text-muted-foreground">Arriba ↔ abajo</span>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="portada-enfoque-x">Encuadre horizontal</Label>
              <input
                id="portada-enfoque-x"
                type="range"
                min={0}
                max={100}
                value={enfoqueX}
                onChange={(e) => setEnfoqueX(Number(e.target.value))}
              />
              <span className="text-xs text-muted-foreground">Izquierda ↔ derecha</span>
            </div>
          </div>

          <Button
            disabled={!puedeGenerar || generarMutation.isPending}
            onClick={() => generarMutation.mutate()}
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
              <Button asChild variant="outline">
                <a href={vistaPrevia} download="portada.png">
                  <Download /> Descargar PNG
                </a>
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
