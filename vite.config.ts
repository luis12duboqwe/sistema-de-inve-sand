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
      alias: {
        '@': resolve(projectRoot, 'src')
      }
    },
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
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
