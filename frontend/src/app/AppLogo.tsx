import { useEffect, useState } from 'react'

import { LOGO_URL } from '@/features/identidad/api'
import logoMarkEstatico from '@/assets/logo-mark.png'

// El logo configurado en Configuración › Identidad comercial es la marca
// de toda la app (sidebar, login, favicon — ver useFaviconIdentidad), no
// solo del informe PDF. GET /identidad-comercial/logo es público
// (app/api/routers/identidad_comercial.py) precisamente para poder
// mostrarse aquí, en LoginPage, antes de que exista una sesión. Cae al
// asset estático cuando todavía no se ha configurado uno.
export function AppLogo({ className, alt = '' }: { className?: string; alt?: string }) {
  const [src, setSrc] = useState(LOGO_URL)

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      onError={() => setSrc(logoMarkEstatico)}
    />
  )
}

// index.html ships static favicon.png/apple-touch-icon.png — this swaps the
// browser-tab icon to the configured logo once (per app load), so it never
// flashes the wrong icon before the check resolves. Silently keeps the
// static default when no logo is configured (or it fails to load) — a
// broken favicon is worse than a generic one.
export function useFaviconIdentidad(): void {
  useEffect(() => {
    const img = new Image()
    img.onload = () => {
      for (const rel of ['icon', 'apple-touch-icon']) {
        const link = document.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`)
        if (link) link.href = LOGO_URL
      }
    }
    img.src = LOGO_URL
  }, [])
}
