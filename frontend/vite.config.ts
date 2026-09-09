import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forward API calls to the nginx gateway (docker compose up) so dev
      // server and prod build behave identically — same origin, no CORS.
      '/api': {
        target: 'http://localhost',
        changeOrigin: true,
      },
    },
  },
})
