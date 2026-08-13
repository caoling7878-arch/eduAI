import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const desktopPkg = JSON.parse(
  readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../../desktop/package.json'), 'utf8'),
) as { version: string }
process.env.VITE_APP_VERSION = desktopPkg.version

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
