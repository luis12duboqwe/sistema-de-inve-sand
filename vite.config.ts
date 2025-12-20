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

  return {
    // En Vitest, los plugins de React (react/refresh) pueden fallar con
    // "can't detect preamble". Para tests, dejamos que Vite/esbuild transformen TSX.
    plugins: [
      (!isTest ? reactSwc() : null) as unknown as PluginOption,
      tailwindcss(),
      // DO NOT REMOVE
      createIconImportProxy() as PluginOption,
      sparkPlugin() as PluginOption,
    ].filter(Boolean) as PluginOption[],
    esbuild: {
      jsx: 'automatic',
    },
    resolve: {
      alias: {
        '@': resolve(projectRoot, 'src')
      }
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
