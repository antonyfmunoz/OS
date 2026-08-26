import { resolve } from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  root: resolve(__dirname, 'src/renderer'),
  envDir: process.env.UMH_WAVE2_VITE_ENV_DIR
    ? resolve(process.env.UMH_WAVE2_VITE_ENV_DIR)
    : resolve(__dirname),
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: resolve(__dirname, 'dist-web'),
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/renderer/index.html'),
        sw: resolve(__dirname, 'src/renderer/sw.ts'),
      },
      output: {
        entryFileNames: (chunkInfo) =>
          chunkInfo.name === 'sw' ? 'sw.js' : 'assets/[name]-[hash].js',
      },
    },
  },
})
