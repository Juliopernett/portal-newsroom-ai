import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Copy, Sparkles } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { solicitudesApi, type DestinoPublicacion } from './api'

const MAX_HASHTAGS = { instagram: 5, facebook: 2 } as const

function contarHashtags(texto: string): number {
  return new Set((texto.match(/(?<!\w)#\w+/gu) ?? []).map((h) => h.toLowerCase())).size
}

// Opcional y a pedido: si el cliente ya trae su texto, no se toca nada.
export function TextoIABlock({
  solicitudId,
  destino,
  onChanged,
}: {
  solicitudId: string
  destino: DestinoPublicacion
  onChanged: () => void
}) {
  const canal = destino.canal === 'instagram' ? 'instagram' : 'facebook'
  const [texto, setTexto] = useState(destino.texto_ia ?? '')
  useEffect(() => setTexto(destino.texto_ia ?? ''), [destino.texto_ia])

  const generar = useMutation({
    mutationFn: (modo: 'ajustar' | 'redactar') =>
      solicitudesApi.generarTextoIA(solicitudId, destino.id, modo),
    onSuccess: () => {
      toast.success('Borrador listo: revísalo y edítalo antes de usarlo.')
      onChanged()
    },
    onError: (err) => toast.error(errorMessage(err)),
  })
  const guardar = useMutation({
    mutationFn: () => solicitudesApi.guardarTextoIA(solicitudId, destino.id, texto),
    onSuccess: () => {
      toast.success('Texto guardado.')
      onChanged()
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const hashtags = contarHashtags(texto)
  const max = MAX_HASHTAGS[canal]
  const ocupado = generar.isPending || guardar.isPending
  const cambiado = texto !== (destino.texto_ia ?? '')

  return (
    <div className="w-full basis-full space-y-2 rounded-md bg-muted/40 p-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium">Texto con IA (opcional)</span>
        <Button size="sm" variant="secondary" disabled={ocupado} onClick={() => generar.mutate('ajustar')}>
          <Sparkles /> Ajustar el texto del cliente
        </Button>
        <Button size="sm" variant="secondary" disabled={ocupado} onClick={() => generar.mutate('redactar')}>
          <Sparkles /> Redactar desde la idea
        </Button>
        {generar.isPending && <span className="text-xs text-muted-foreground">Generando…</span>}
      </div>
      {(destino.texto_ia || texto) && (
        <>
          <Textarea
            rows={5}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            aria-label={`Texto para ${canal}`}
          />
          <div className="flex flex-wrap items-center gap-2">
            <span className={`text-xs ${hashtags > max ? 'text-danger' : 'text-muted-foreground'}`}>
              {hashtags}/{max} hashtags · {texto.length} caracteres
            </span>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => navigator.clipboard.writeText(texto).then(() => toast.success('Copiado.'))}
            >
              <Copy /> Copiar
            </Button>
            <Button size="sm" disabled={ocupado || !cambiado || hashtags > max} onClick={() => guardar.mutate()}>
              Guardar cambios
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
