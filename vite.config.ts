import tailwindcss from "@tailwindcss/vite";
import reactSwc from "@vitejs/plugin-react-swc";
import { defineConfig, PluginOption } from "vite";

import sparkPlugin from "@github/spark/spark-vite-plugin";
import createIconImportProxy from "@github/spark/vitePhosphorIconProxyPlugin";
import { resolve } from 'path'

const projectRoot = process.env.PROJECT_ROOT || import.meta.dirname

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const isTest = mode === 'test' || Boolean(process.env.VITEST)
  const isDevelopment = mode === 'development'

  return {
    // En Vitest, los plugins de React (react/refresh) pueden fallar con
    // "can't detect preamble". Para tests, dejamos que Vite/esbuild transformen TSX.
    plugins: [
      (!isTest ? reactSwc() : null) as unknown as PluginOption,
      tailwindcss(),
      // DO NOT REMOVE
      createIconImportProxy() as PluginOption,
      (!isDevelopment ? sparkPlugin() : null) as unknown as PluginOption,
      (isDevelopment
        ? {
            name: 'spark-loaded-noop',
            configureServer(server) {
              server.middlewares.use('/_spark/loaded', (req, res, next) => {
                if (req.method === 'POST') {
                  res.statusCode = 204
                  res.end()
                  return
                }
                next()
              })
            },
          }
        : null) as unknown as PluginOption,
    ].filter(Boolean) as PluginOption[],
    esbuild: {
      jsx: 'automatic',
    },
    resolve: {
      alias: [
        { find: '@', replacement: resolve(projectRoot, 'src') },
        { find: /^@phosphor-icons\/react$/, replacement: resolve(projectRoot, 'src/lib/icon-proxies/phosphor.ts') },
        { find: /^lucide-react$/, replacement: resolve(projectRoot, 'src/lib/icon-proxies/lucide.ts') },
      ]
    },
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      chunkSizeWarningLimit: 1300,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return undefined
            if (id.includes('/react/') || id.includes('/react-dom/') || id.includes('/scheduler/')) return 'react'
            if (id.includes('/@tanstack/react-query/')) return 'query'
            if (id.includes('/react-hook-form/') || id.includes('/@hookform/')) return 'forms'
            if (id.includes('/@radix-ui/')) return 'radix'
            if (id.includes('/@phosphor-icons/') || id.includes('/lucide-react/')) return 'icons'
            if (id.includes('/framer-motion/')) return 'motion'
            if (id.includes('/recharts/') || id.includes('/d3-')) return 'charts'
            if (id.includes('/date-fns/')) return 'date-fns'
            return undefined
          },
        },
      },
    },
    test: {
      environment: 'happy-dom',
      globals: true,
      setupFiles: './src/test/setup.ts',
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov']
      },
      alias: {
        '@': resolve(projectRoot, 'src')
      }
    }
  }
});
