import { useState } from 'react'
import { Loader2 } from 'lucide-react'

import { errorMessage } from '@/api/client'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SelectNative } from '@/components/ui/select-native'
import type { OpcionesPortada } from '@/features/radar/api'

// «Crear borrador» de WordPress con la portada opcional: igual que «Crear noticia» del
// Radar, se sube la foto, se escoge el titular y la portada queda armada de una vez como
// imagen destacada. Sin foto, el borrador usa la primera imagen adjunta (si hay).
export function CrearBorradorDialog({
  idBase,
  disabled,
  crear,
}: {
  idBase: string
  disabled: boolean
  crear: (portada: OpcionesPortada | null) => Promise<unknown>
}) {
  const [abierto, setAbierto] = useState(false)
  const [pendiente, setPendiente] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [imagenBase, setImagenBase] = useState<File | null>(null)
  const [imagenCirculo, setImagenCirculo] = useState<File | null>(null)
  const [variante, setVariante] = useState<OpcionesPortada['variante']>('noticias')
  const [titular, setTitular] = useState('')
  const [antetitulo, setAntetitulo] = useState('')

  async function confirmar() {
    setPendiente(true)
    setError(null)
    try {
      await crear(imagenBase ? { imagenBase, imagenCirculo, variante, titular, antetitulo } : null)
      setAbierto(false)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setPendiente(false)
    }
  }

  return (
    <AlertDialog
      open={abierto}
      onOpenChange={(abrir) => {
        if (pendiente) return
        if (abrir) setError(null)
        setAbierto(abrir)
      }}
    >
      <AlertDialogTrigger asChild>
        <Button size="sm" variant="secondary" disabled={disabled}>
          Crear borrador
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Crear borrador en WordPress</AlertDialogTitle>
          <AlertDialogDescription>
            La IA prepara el texto y se deja un BORRADOR en WordPress: nada se publica hasta que
            lo revises allá. Puede tardar unos segundos.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="flex flex-col gap-3 rounded-md border border-border p-3">
          <p className="text-sm font-medium">Portada (opcional)</p>
          <p className="text-xs text-muted-foreground">
            Sube tu foto y se arma la portada con la plantilla de Portal Vallenato: queda como
            imagen destacada del borrador y la puedes bajar para redes. Sin foto, el borrador usa
            la primera imagen adjunta de la solicitud, si la hay.
          </p>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor={`portada-foto-${idBase}`}>Foto base</Label>
            <Input
              id={`portada-foto-${idBase}`}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setImagenBase(e.target.files?.[0] ?? null)}
            />
          </div>
          {imagenBase && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor={`portada-plantilla-${idBase}`}>Plantilla</Label>
                  <SelectNative
                    id={`portada-plantilla-${idBase}`}
                    value={variante}
                    onChange={(e) => setVariante(e.target.value as OpcionesPortada['variante'])}
                  >
                    <option value="noticias">Noticias</option>
                    <option value="lo_ultimo">Lo último</option>
                  </SelectNative>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor={`portada-circulo-${idBase}`}>Foto en círculo</Label>
                  <Input
                    id={`portada-circulo-${idBase}`}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(e) => setImagenCirculo(e.target.files?.[0] ?? null)}
                  />
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor={`portada-antetitulo-${idBase}`}>
                  Antetítulo (ej. ¡CONFIRMADO!)
                </Label>
                <Input
                  id={`portada-antetitulo-${idBase}`}
                  maxLength={60}
                  value={antetitulo}
                  onChange={(e) => setAntetitulo(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor={`portada-titular-${idBase}`}>Titular de la portada</Label>
                <Input
                  id={`portada-titular-${idBase}`}
                  placeholder="Vacío = el titular del borrador (el que redacte la IA)"
                  maxLength={200}
                  value={titular}
                  onChange={(e) => setTitular(e.target.value)}
                />
              </div>
            </>
          )}
        </div>

        {pendiente && (
          <p role="status" className="flex items-center gap-2 rounded-md bg-muted p-3 text-sm">
            <Loader2 className="size-4 shrink-0 animate-spin" />
            Preparando con IA y creando el borrador… no cierres esta ventana.
          </p>
        )}
        {error && (
          <p
            role="alert"
            className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
          >
            No se pudo crear el borrador: {error}
          </p>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={pendiente}>Volver</AlertDialogCancel>
          <AlertDialogAction
            disabled={pendiente}
            onClick={(e) => {
              // No cerrar: el diálogo se cierra solo al terminar bien.
              e.preventDefault()
              void confirmar()
            }}
          >
            {error ? 'Reintentar' : 'Crear borrador'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
