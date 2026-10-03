import { defineConfig, type ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'node:fs'
import path from 'node:path'

// Dev only: `npm run dev` proxies /api to the Python backend (DASH_API, default http://127.0.0.1:8787).
// The backend needs Basic auth or the session cookie; the proxy injects an Authorization header built from the
// `user:pass` file named by DASH_AUTH_FILE, read once at dev-server start. The value is never logged or written.
// Writes (POST/PUT/DELETE) are refused by the proxy unless DASH_ALLOW_WRITES=1, so a dev session pointed at the
// live lab cannot change parameters by accident. Production build: same-origin, nothing injected.
function devProxy(): Record<string, ProxyOptions> {
  const target = process.env.DASH_API || 'http://127.0.0.1:8787'
  let auth: string | undefined
  const file = process.env.DASH_AUTH_FILE
  if (file) {
    try {
      const raw = fs.readFileSync(file.replace(/^~(?=\/)/, process.env.HOME || '~'), 'utf8').trim()
      if (raw.includes(':')) auth = 'Basic ' + Buffer.from(raw).toString('base64')
      else console.warn('[dev proxy] DASH_AUTH_FILE não tem o formato user:pass; seguindo sem auth')
    } catch {
      console.warn('[dev proxy] não consegui ler DASH_AUTH_FILE; seguindo sem auth')
    }
  }
  const allowWrites = process.env.DASH_ALLOW_WRITES === '1'
  return {
    '/api': {
      target,
      changeOrigin: true,
      configure(proxy) {
        proxy.on('proxyReq', (req, inc) => {
          if (auth) req.setHeader('Authorization', auth)
          if (!allowWrites && inc.method && inc.method !== 'GET' && inc.method !== 'HEAD') req.destroy()
        })
        proxy.on('error', (_err, req, res) => {
          const r = res as import('node:http').ServerResponse
          if ('writeHead' in r && !r.headersSent) {
            const blocked = !allowWrites && req.method !== 'GET' && req.method !== 'HEAD'
            r.writeHead(blocked ? 403 : 502, { 'Content-Type': 'application/json' })
            r.end(JSON.stringify({ detail: blocked ? 'Modo de desenvolvimento: gravações bloqueadas (DASH_ALLOW_WRITES=1 libera).' : 'Backend indisponível' }))
          }
        })
      },
    },
  }
}

export default defineConfig(({ command }) => ({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: command === 'serve' ? { proxy: devProxy() } : undefined,
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('lightweight-charts') || id.includes('fancy-canvas')) return 'charts'
          if (id.includes('@radix-ui') || id.includes('sonner')) return 'ui'
          if (id.includes('node_modules')) return 'vendor'
        },
      },
    },
  },
}))
