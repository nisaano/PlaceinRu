import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// Проксируем запросы через Vite, чтобы браузеру не требовался CORS на API.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxy = (prefix, target) => ({
    target,
    changeOrigin: true,
    rewrite: (path) => path.substring(prefix.length),
  })

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/backend': apiProxy('/backend', env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8080'),
        '/mrt': apiProxy('/mrt', env.VITE_MRT_PROXY_TARGET || 'http://localhost:8010'),
      },
    },
  }
})
