import { Copy } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { formatFechaHoraNegocio } from '@/lib/format'
import type { NewsCandidate } from './api'

const HASHTAGS_FIJOS = '#NoticiasVallenatas #portalvallenato'

const WP_BADGE: Record<string, { label: string; className: string }> = {
  borrador: { label: 'Borrador en WordPress', className: 'bg-warning-bg text-warning' },
  publicado: { label: 'Publicada', className: 'bg-success-bg text-success' },
  eliminado: { label: 'En la papelera', className: 'bg-muted text-muted-foreground' },
}

// El enlace de Instagram no es pulsable en un texto, por eso ahí se manda a
// la bio; en Facebook sí va el enlace de la nota ya publicada.
function textoFacebook(c: NewsCandidate): string {
  return `${c.texto_redes}\n\n👉 Lee la nota completa en Portal Vallenato: ${c.wp_publicado_url}\n\n${HASHTAGS_FIJOS}`
}

function textoInstagram(c: NewsCandidate): string {
  return `${c.texto_redes}\n\n👉 Lee la nota completa en portalvallenato.com — link en la bio.\n\n${HASHTAGS_FIJOS}`
}

async function copiar(texto: string, red: string) {
  try {
    await navigator.clipboard.writeText(texto)
    toast.success(`Texto de ${red} copiado.`)
  } catch {
    toast.error('No se pudo copiar — selecciona el texto y cópialo a mano.')
  }
}

/** Estado de WordPress + paquete para redes de un candidato ya procesado. */
export function PanelPublicacion({ candidato }: { candidato: NewsCandidate }) {
  const badge = candidato.wp_estado ? WP_BADGE[candidato.wp_estado] : null
  const publicada = candidato.wp_estado === 'publicado'

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-muted/30 p-2 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        {badge ? (
          <span className={`rounded-full px-2 py-0.5 ${badge.className}`}>{badge.label}</span>
        ) : (
          <span className="text-muted-foreground">Estado en WordPress sin verificar</span>
        )}
        {publicada && candidato.wp_fecha_publicacion && (
          <span className="text-muted-foreground">
            {formatFechaHoraNegocio(candidato.wp_fecha_publicacion)}
          </span>
        )}
        {publicada && candidato.wp_publicado_url && (
          <a
            href={candidato.wp_publicado_url}
            target="_blank"
            rel="noopener"
            className="font-medium text-brand underline"
          >
            Ver nota publicada
          </a>
        )}
      </div>

      {candidato.texto_redes &&
        (publicada ? (
          <div className="flex flex-col gap-2">
            <p className="font-medium text-foreground">Texto para redes</p>
            <p className="whitespace-pre-line text-muted-foreground">{candidato.texto_redes}</p>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => copiar(textoFacebook(candidato), 'Facebook')}
              >
                <Copy /> Copiar texto Facebook
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => copiar(textoInstagram(candidato), 'Instagram')}
              >
                <Copy /> Copiar texto Instagram
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground">
            Publica la nota en WordPress para habilitar el texto de redes — necesita el enlace
            definitivo de la nota.
          </p>
        ))}
    </div>
  )
}
