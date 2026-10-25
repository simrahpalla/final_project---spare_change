import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In production FastAPI serves frontend/dist and the API from the same origin.
// In development (npm run dev), /api is proxied to the backend on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': 'http://localhost:8000' },
  },
})
