import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // In dev, proxy /api calls to the backend so you don't hit CORS
  // This only applies when running `npm run dev` locally
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  build: {
    // Output to dist/ — FastAPI will serve this
    outDir: 'dist',
  }
})
