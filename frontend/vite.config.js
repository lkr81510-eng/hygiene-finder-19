import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 개발 시 /api 요청을 FastAPI(8000)로 프록시. 배포 시에는 nginx 가 같은 역할을 한다.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
