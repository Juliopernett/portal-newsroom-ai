import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Bookmark, ChevronDown, ChevronUp, ExternalLink, Newspaper, Sparkles, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

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
import { errorMessage } from '@/api/client'
import { formatFechaHoraNegocio } from '@/lib/format'
import { formatHoras, horasEnEspera } from '@/features/solicitudes/utils'
import { radarApi, type NewsCandidate } from './api'

const ESTADO_LABELS: Record<NewsCandidate['estado'], string> = {
  nuevo: 'Nuevo',
  guardado: 'Guardado',
  descartado: 'Descartado',
  procesado: 'Procesado',
}

const ESTADO_BADGE: Record<NewsCandidate['estado'], string> = {
  nuevo: 'bg-brand/10 text-brand',
  guardado: 'bg-success-bg text-success',
  descartado: 'bg-muted text-muted-foreground',
  procesado: 'bg-warning-bg text-warning',
}

const RADAR_KEY = ['radar-candidatos']

export function RadarCandidateCard({ candidato }: { candidato: NewsCandidate }) {
  const queryClient = useQueryClient()
  const [mostrarContenido, setMostrarContenido] = useState(false)

  function onExito(mensaje: string) {
    queryClient.invalidateQueries({ queryKey: RADAR_KEY })
    toast.success(mensaje)
  }

  const guardarMutation = useMutation({
    mutationFn: () => radarApi.guardar(candidato.id),
    onSuccess: () => onExito('Candidato guardado.'),
    onError: (err) => toast.error(errorMessage(err)),
  })
  const descartarMutation = useMutation({
    mutationFn: () => radarApi.descartar(candidato.id),
    onSuccess: () => onExito('Candidato descartado.'),
    onError: (err) => toast.error(errorMessage(err)),
  })
  const crearNoticiaMutation = useMutation({
    mutationFn: () => radarApi.crearNoticia(candidato.id),
    onSuccess: () => onExito('Candidato marcado para crear noticia.'),
    onError: (err) => toast.error(errorMessage(err)),
  })
  const prepararMutation = useMutation({
    mutationFn: () => radarApi.preparar(candidato.id),
    onSuccess: (actualizado) => {
      queryClient.invalidateQueries({ queryKey: RADAR_KEY })
      if (actualizado.estado_resolucion === 'resuelta') {
        toast.success(
          actualizado.extracted_content
            ? 'Fuente resuelta y contenido extraído.'
            : 'Fuente resuelta, pero no se pudo extraer el contenido todavía.',
        )
      } else {
        toast.error('No se pudo resolver la fuente original — puedes volver a intentar más tarde.')
      }
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const isActing =
    guardarMutation.isPending ||
    descartarMutation.isPending ||
    crearNoticiaMutation.isPending ||
    prepararMutation.isPending
  const esTerminal = candidato.estado === 'procesado'

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="font-medium">{candidato.title}</p>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${ESTADO_BADGE[candidato.estado]}`}>
          {ESTADO_LABELS[candidato.estado]}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span className="rounded-full bg-muted px-2 py-0.5">{candidato.source}</span>
        <span>
          Publicado:{' '}
          {candidato.published_at ? formatFechaHoraNegocio(candidato.published_at) : 'Sin fecha'}
        </span>
        <span>Descubierto {formatHoras(horasEnEspera(candidato.discovered_at))}</span>
      </div>

      <p className="text-sm text-muted-foreground">
        {candidato.summary || 'Sin resumen disponible.'}
      </p>

      <div className="flex flex-wrap items-center gap-2">
        {candidato.estado_resolucion === 'resuelta' && candidato.url_fuente_original ? (
          <a
            href={candidato.url_fuente_original}
            target="_blank"
            rel="noopener"
            title="URL real del medio, resuelta a partir del enlace de Google Noticias"
            className="inline-flex items-center gap-1 text-xs font-medium text-brand underline"
          >
            <ExternalLink className="size-3.5" /> Fuente original
          </a>
        ) : candidato.estado_resolucion === 'fallida' ? (
          <span className="text-xs text-destructive">No se pudo resolver la fuente</span>
        ) : (
          <span className="text-xs text-muted-foreground">Fuente pendiente de resolver</span>
        )}

        <a
          href={candidato.url}
          target="_blank"
          rel="noopener"
          title="Enlace de Google Noticias — puede no ser la URL del medio original"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground underline"
        >
          <ExternalLink className="size-3.5" /> Ver descubrimiento
        </a>

        {!esTerminal && (
          <>
            <Button
              size="sm"
              variant="outline"
              disabled={isActing}
              onClick={() => prepararMutation.mutate()}
            >
              <Sparkles /> Preparar noticia
            </Button>

            {candidato.estado !== 'guardado' && (
              <Button
                size="sm"
                variant="secondary"
                disabled={isActing}
                onClick={() => guardarMutation.mutate()}
              >
                <Bookmark /> Guardar
              </Button>
            )}

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" variant="secondary" disabled={isActing}>
                  <Trash2 /> Descartar
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>¿Descartar este candidato?</AlertDialogTitle>
                  <AlertDialogDescription>
                    No se elimina de la base de datos — solo deja de mostrarse como pendiente.
                    Puedes guardarlo más tarde si cambias de opinión.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Volver</AlertDialogCancel>
                  <AlertDialogAction onClick={() => descartarMutation.mutate()}>
                    Sí, descartar
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" disabled={isActing}>
                  <Newspaper /> Crear noticia
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>¿Crear noticia a partir de este candidato?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Por ahora esto solo marca el candidato como "Procesado" y lo prepara para el
                    flujo editorial — la redacción automática con IA (Writer) todavía no existe,
                    llega en un sprint futuro. Es una acción terminal: no podrás volver a
                    guardarlo/descartarlo después.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Volver</AlertDialogCancel>
                  <AlertDialogAction onClick={() => crearNoticiaMutation.mutate()}>
                    Sí, marcar para crear noticia
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </>
        )}
      </div>

      {candidato.extracted_content && (
        <div className="rounded-md border border-border bg-muted/40 p-2 text-xs">
          <button
            type="button"
            onClick={() => setMostrarContenido((v) => !v)}
            className="flex w-full items-center justify-between gap-2 font-medium text-foreground"
          >
            <span>
              Contenido extraído
              {candidato.extracted_content.site_name ? ` — ${candidato.extracted_content.site_name}` : ''}
            </span>
            {mostrarContenido ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
          </button>
          {mostrarContenido && (
            <div className="mt-2 space-y-1 text-muted-foreground">
              <p className="font-medium text-foreground">{candidato.extracted_content.title}</p>
              {candidato.extracted_content.author && <p>Autor: {candidato.extracted_content.author}</p>}
              <p className="whitespace-pre-line">{candidato.extracted_content.body}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
