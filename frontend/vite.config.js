import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Минимальная конфигурация сборки: React Fast Refresh в разработке и JSX-трансформация.
export default defineConfig({
  plugins: [react()],
})
