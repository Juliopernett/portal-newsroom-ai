import { useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2, Upload } from 'lucide-react'
import { toast } from 'sonner'

import { errorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { solicitudesApi } from './api'
import { MEDIA_TIPO_LABELS, formatBytes } from './utils'

export function MediaPanel({ solicitudId, esPublicada }: { solicitudId: string; esPublicada: boolean }) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const key = ['media', solicitudId]

  const mediaQuery = useQuery({ queryKey: key, queryFn: () => solicitudesApi.listMedia(solicitudId) })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => solicitudesApi.uploadMedia(solicitudId, file),
    onSuccess: () => {
      toast.success('Archivo subido.')
      queryClient.invalidateQueries({ queryKey: key })
      if (fileInputRef.current) fileInputRef.current.value = ''
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: (mediaId: string) => solicitudesApi.deleteMedia(solicitudId, mediaId),
    onSuccess: () => {
      toast.success('Archivo eliminado.')
      queryClient.invalidateQueries({ queryKey: key })
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const media = mediaQuery.data ?? []

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-background p-3 text-sm">
      {mediaQuery.isLoading ? (
        <p className="text-muted-foreground">Cargando…</p>
      ) : media.length === 0 ? (
        <p className="text-muted-foreground">Sin archivos adjuntos todavía.</p>
      ) : (
        <div className="flex flex-col divide-y divide-border">
          {media.map((m) => (
            <div key={m.id} className="flex flex-wrap items-center gap-3 py-1.5">
              <span className="text-xs text-muted-foreground">{MEDIA_TIPO_LABELS[m.tipo]}</span>
              <span className="flex-1 truncate">{m.nombre_archivo}</span>
              <span className="text-xs text-muted-foreground">{formatBytes(m.tamano_bytes)}</span>
              <a
                className="text-xs text-brand underline"
                href={solicitudesApi.mediaContentUrl(solicitudId, m.id)}
                target="_blank"
                rel="noopener"
              >
                Ver
              </a>
              <Button
                variant="ghost"
                size="sm"
                className="text-danger hover:text-danger"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(m.id)}
              >
                <Trash2 /> Eliminar
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Omitted entirely (not just disabled) once completa — matches
          the legacy app: uploading to a closed solicitud 409s, and the
          form's absence explains why without the operator having to
          hit that error first. */}
      {!esPublicada && (
        <div className="flex items-center gap-2 border-t border-border pt-2">
          <Upload className="size-4 shrink-0 text-muted-foreground" />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            disabled={uploadMutation.isPending}
            className="text-xs"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) uploadMutation.mutate(file)
            }}
          />
          {uploadMutation.isPending && <span className="text-xs text-muted-foreground">Subiendo…</span>}
        </div>
      )}
    </div>
  )
}
