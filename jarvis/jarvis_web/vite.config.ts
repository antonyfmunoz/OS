import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    proxy: {
      '/api/jarvis': 'http://localhost:8093',
      '/ws': { target: 'ws://localhost:8093', ws: true },
    },
  },
})
