import path from 'node:path'
import { defineConfig, type ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Several backend routers (see app/api/main.py) live at the exact same
// top-level path as one of our client-side routes — /gastos, /clientes,
// /dashboard... A full-page browser navigation to e.g. /gastos must
// still get the SPA (index.html), not the raw JSON the backend would
// return; only an actual fetch()/XHR call from inside the app should be
// proxied through. Browsers send `Accept: text/html...` on navigations
// and `*/*` (never text/html) on fetch(), so that header reliably tells
// the two apart — this only matters for the dev proxy: in production,
// FastAPI serves the built frontend and the API from the same origin
// with no proxy involved, so this ambiguity doesn't exist there.
function backendProxy(): ProxyOptions {
  return {
    target: 'http://localhost:8000',
    bypass(req) {
      if (req.headers.accept?.includes('text/html')) return '/index.html'
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
      '/publication-requests': backendProxy(),
      '/reportes': backendProxy(),
    },
  },
})
