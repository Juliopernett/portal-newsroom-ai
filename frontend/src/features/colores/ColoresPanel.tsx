import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Eye, Loader2, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { COLORES_WEB, coloresApi, type ColoresMarca } from './api'
import { avisosDeContraste } from './contraste'

const COLORES_KEY = ['colores-marca']
const ES_COLOR = /^#[0-9A-Fa-f]{6}$/

const CAMPOS: { campo: keyof ColoresMarca; label: string; ayuda: string }[] = [
  { campo: 'fondo', label: 'Fondo', ayuda: 'Degradado de las portadas y fondo del Radar.' },
  { campo: 'destacado', label: 'Destacado', ayuda: 'Botón del gancho y acentos del Radar.' },
  {
    campo: 'texto_destacado',
    label: 'Texto sobre el destacado',
    ayuda: 'Letra del gancho y números del Radar.',
  },
]

export function ColoresPanel() {
  const coloresQuery = useQuery({ queryKey: COLORES_KEY, queryFn: coloresApi.get })

  if (coloresQuery.isError)
    return <p className="text-sm text-destructive">{errorMessage(coloresQuery.error)}</p>
  if (!coloresQuery.data) return <p className="text-sm text-muted-foreground">Cargando…</p>
  return <Editor guardados={coloresQuery.data} />
}

function Editor({ guardados }: { guardados: ColoresMarca }) {
  const queryClient = useQueryClient()
  const [colores, setColores] = useState(guardados)
  const [previas, setPrevias] = useState<string[]>([])

  useEffect(() => {
    return () => previas.forEach((url) => URL.revokeObjectURL(url))
  }, [previas])

  const validos = CAMPOS.every(({ campo }) => ES_COLOR.test(colores[campo]))
  const sinCambios = CAMPOS.every(
    ({ campo }) => colores[campo].toUpperCase() === guardados[campo].toUpperCase(),
  )
  const avisos = validos ? avisosDeContraste(colores) : []

  const previaMutation = useMutation({
    mutationFn: (c: ColoresMarca) =>
      Promise.all([coloresApi.vistaPrevia('portada', c), coloresApi.vistaPrevia('radar', c)]),
    onSuccess: (blobs) => setPrevias(blobs.map((b) => URL.createObjectURL(b))),
    onError: (err) => toast.error(errorMessage(err)),
  })
  const guardarMutation = useMutation({
    mutationFn: coloresApi.save,
    onSuccess: (nuevos) => {
      queryClient.setQueryData(COLORES_KEY, nuevos)
      setColores(nuevos)
      toast.success('Colores guardados: las próximas imágenes ya salen con ellos.')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Se usan en las portadas (Portadas, Radar y Solicitudes) y en las tarjetas del Radar
        Vallenato. Las imágenes ya creadas no cambian.
      </p>

      <div className="grid gap-4 sm:grid-cols-3">
        {CAMPOS.map(({ campo, label, ayuda }) => (
          <div key={campo} className="flex flex-col gap-1.5">
            <Label htmlFor={`color-${campo}`}>{label}</Label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                aria-label={`Elegir ${label.toLowerCase()}`}
                className="size-10 shrink-0 cursor-pointer rounded-md border border-border"
                value={ES_COLOR.test(colores[campo]) ? colores[campo].toLowerCase() : '#000000'}
                onChange={(e) => setColores({ ...colores, [campo]: e.target.value.toUpperCase() })}
              />
              <Input
                id={`color-${campo}`}
                maxLength={7}
                value={colores[campo]}
                aria-invalid={!ES_COLOR.test(colores[campo])}
                onChange={(e) => setColores({ ...colores, [campo]: e.target.value.trim() })}
              />
            </div>
            <p className="text-xs text-muted-foreground">{ayuda}</p>
          </div>
        ))}
      </div>

      {!validos && (
        <p role="alert" className="text-sm text-destructive">
          Escribe cada color con el formato #3B5998.
        </p>
      )}
      {avisos.length > 0 && (
        <ul
          role="status"
          className="list-inside list-disc rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm"
        >
          {avisos.map((aviso) => (
            <li key={aviso}>{aviso}</li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          disabled={!validos || previaMutation.isPending}
          onClick={() => previaMutation.mutate(colores)}
        >
          {previaMutation.isPending ? <Loader2 className="animate-spin" /> : <Eye />}
          Ver vista previa
        </Button>
        <Button
          disabled={!validos || sinCambios || guardarMutation.isPending}
          onClick={() => guardarMutation.mutate(colores)}
        >
          Guardar colores
        </Button>
        <Button variant="secondary" onClick={() => setColores(COLORES_WEB)}>
          <RotateCcw /> Usar los de la web
        </Button>
      </div>

      {previas.length > 0 && (
        <div className="grid max-w-2xl grid-cols-2 gap-3">
          {previas.map((url, i) => (
            <img
              key={url}
              src={url}
              alt={i === 0 ? 'Portada de muestra' : 'Tarjeta del Radar de muestra'}
              className="w-full rounded-lg border border-border"
            />
          ))}
        </div>
      )}
    </div>
  )
}
