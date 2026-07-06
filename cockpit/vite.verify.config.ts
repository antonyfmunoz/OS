// WP-P4-COCKPIT-BROWSER-VERIFY-001 — local verification runtime config.
//
// Serves the web cockpit on the Tailscale interface only, with /api/umh
// same-origin-proxied to the real backend (os-operator, 127.0.0.1:8091) —
// the same shape production nginx uses on Fly. No Clerk key is provided, so
// the app runs its supported no-auth dev mode; the backend's private-IP dev
// bypass governs API access. Verification harness only — not a deploy path.
import { resolve } from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const TAILSCALE_HOST = process.env.VERIFY_HOST || '0.0.0.0'

export default defineConfig({
  root: resolve(__dirname, 'src/renderer'),
  envDir: resolve(__dirname, 'verify-env-empty'), // no .env pickup — defaults only
  plugins: [react(), tailwindcss()],
  server: {
    host: TAILSCALE_HOST,
    port: 5199,
    strictPort: true,
    proxy: {
      '/api/umh': {
        target: 'http://127.0.0.1:8091',
        changeOrigin: true,
      },
    },
  },
})
