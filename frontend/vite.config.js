import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backend = process.env.VITE_BACKEND || 'http://127.0.0.1:5000'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // dev only: forward API + product images to the Flask backend
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/static': { target: backend, changeOrigin: true }
    }
  },
  build: { outDir: 'dist', chunkSizeWarningLimit: 900 }
})
