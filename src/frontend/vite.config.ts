import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  optimizeDeps: {
    // Pre-bundle up front so the first page load never mixes stale and fresh dependency bundles.
    include: [
      'react',
      'react-dom/client',
      'react-router',
      '@tanstack/react-query',
      'react-hook-form',
      '@hookform/resolvers/zod',
      'zod',
      'radix-ui',
      'sonner',
      'lucide-react',
      'clsx',
      'tailwind-merge',
      'class-variance-authority',
    ],
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // API calls go through the dev server, so the browser sees a single origin (no CORS).
      '/api': process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
    },
  },
})
