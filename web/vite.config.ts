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
    // Giao diện chạy cố định ở cổng 3000; cổng bận thì báo lỗi thay vì tự đổi cổng khác.
    port: 3000,
    strictPort: true,
    // Dùng 127.0.0.1 thay cho localhost để tránh lệch IPv6 (::1) trên WSL
    proxy: { '/api': 'http://127.0.0.1:8000' },
    allowedHosts: [
      'ubuntu-36.bitterling-butterfly.ts.net'
    ]
  },
})
