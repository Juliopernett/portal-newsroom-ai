import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

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
      // own top-level path (see app/api/main.py's include_router calls).
      '/auth': 'http://localhost:8000',
      '/clients': 'http://localhost:8000',
      '/dashboard': 'http://localhost:8000',
      '/gastos': 'http://localhost:8000',
      '/insights': 'http://localhost:8000',
      '/pautas': 'http://localhost:8000',
      '/publication-requests': 'http://localhost:8000',
      '/reportes': 'http://localhost:8000',
    },
  },
})
