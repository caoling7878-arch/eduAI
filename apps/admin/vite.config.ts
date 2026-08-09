import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // 桌面/生产由 API 挂载在 /admin
  base: process.env.EDUAI_ADMIN_BASE || '/',
  server: {
    port: 5174,
    proxy: {
      // 用 /api/v1，避免与前端路由 /api-tokens 冲突
      '/api/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
