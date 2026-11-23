import { toast } from 'sonner'

import { errorMessage } from '@/api/client'

// Guarda un archivo ya descargado. En teléfonos/tabletas (pantalla táctil) abre la hoja de
// compartir (galería, WhatsApp, Instagram...); en escritorio lo descarga directo (en
// Windows `canShare` también da verdadero y abriría el diálogo de compartir sin querer).
export async function guardarBlob(blob: Blob, nombre: string): Promise<void> {
  const archivo = new File([blob], nombre, { type: blob.type })
  const esTactil = window.matchMedia('(pointer: coarse)').matches
  if (esTactil && navigator.canShare?.({ files: [archivo] })) {
    try {
      await navigator.share({ files: [archivo] })
      return
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return
    }
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nombre
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}

// Baja un archivo del backend con la sesión (cookie) y lo guarda. Un enlace directo con
// `download` o `target=_blank` falla en el teléfono: el gestor de descargas no lleva la
// cookie y guarda la página HTML de login en vez del archivo.
export async function descargarArchivo(url: string, nombre: string): Promise<void> {
  try {
    const res = await fetch(url, { credentials: 'include' })
    const tipo = res.headers.get('content-type') ?? ''
    if (!res.ok || tipo.startsWith('text/html')) {
      throw new Error(
        res.ok || res.status === 401
          ? 'La sesión venció: vuelve a entrar e inténtalo de nuevo'
          : `Error ${res.status}`,
      )
    }
    await guardarBlob(await res.blob(), nombre)
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
