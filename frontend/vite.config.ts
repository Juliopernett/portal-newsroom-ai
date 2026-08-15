import path from 'node:path'
import { defineConfig, type ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// A few backend routers (see app/api/main.py) live at the exact same
// top-level path as one of our client-side routes — currently /gastos
// and /reportes. A full-page browser navigation to e.g. /gastos must
// still get the SPA (index.html), not the raw JSON the backend would
// return; only an actual fetch()/XHR call from inside the app should be
// proxied through. Browsers send `Accept: text/html...` on navigations
// and `*/*` (never text/html) on fetch(), so that header reliably tells
// the two apart. This only matters for the dev proxy: in production,
// FastAPI serves the built frontend and the API from the same origin
// with no proxy involved, so this ambiguity doesn't exist there.
//
// /reportes is trickier: /reportes itself is a client route, but
// /reportes/*.csv are real file-download endpoints that ALSO navigate
// as a full-page document (target="_blank" links, same as the browser
// address bar) and must always reach the backend. So the SPA bypass
// there has to match the exact client-route path, not the whole
// proxied prefix — matchPath lets each entry opt into that.
//
// /publication-requests has the same problem one level deeper: no
// client route lives at that path (the client route is /solicitudes),
// but /publication-requests/{id}/media/{mediaId}/contenido is a real
// file (opened via target="_blank", same as a CSV download) that must
// never be swallowed by the SPA fallback — pass `false` to disable the
// bypass for a prefix entirely.
function backendProxy(matchPath?: string | false): ProxyOptions {
  return {
    target: 'http://localhost:8000',
    bypass(req) {
      if (matchPath === false) return
      if (!req.headers.accept?.includes('text/html')) return
      if (matchPath && req.url?.split('?')[0] !== matchPath) return
      return '/index.html'
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    proxy: {
      // No global "/api" prefix on the backend — each router owns its
      // own top-level path.
      '/auth': backendProxy(),
      '/clients': backendProxy(),
      '/dashboard': backendProxy(),
      '/gastos': backendProxy(),
      '/insights': backendProxy(),
      '/pautas': backendProxy(),
      '/publication-requests': backendProxy(false),
      '/reportes': backendProxy('/reportes'),
    },
  },
})
