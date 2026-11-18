import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    // Dùng 127.0.0.1 thay cho localhost để tránh lệch IPv6 (::1) trên WSL
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
