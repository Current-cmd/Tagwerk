import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const API = process.env.TAGWERK_API ?? 'http://localhost:8080'

// Built into ../web/app (committed): the FastAPI app serves it under /app/ without Node.
export default defineConfig({
  base: '/app/',
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, './src') } },
  build: {
    outDir: '../web/app',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1200,
  },
  server: {
    proxy: {
      '/api': API,
      '/health': API,
      '/captures': API,
      '/media': API,
      '/events': { target: API.replace(/^http/, 'ws'), ws: true },
    },
  },
})
