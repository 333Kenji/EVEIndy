import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/analytics': 'http://localhost:8000',
      '/plan': 'http://localhost:8000',
      '/health': 'http://localhost:8000'
    }
  }
})

