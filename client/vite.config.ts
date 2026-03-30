import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // api/convert.py serves POST / on port 8000; map /api/convert → /
    proxy: {
      '/api/convert': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/convert\/?$/, '/') || '/',
      },
    },
  },
})

