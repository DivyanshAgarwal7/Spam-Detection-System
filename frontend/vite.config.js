import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(),tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:3000',
      '/predict': 'http://localhost:3000',
      '/feedback': 'http://localhost:3000',
      '/analyze-email-header': 'http://localhost:3000',
      '/bulk-predict': 'http://localhost:3000',
    },
  },
})
