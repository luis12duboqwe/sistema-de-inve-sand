import { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { updateApiUrl } from '@/lib/apiClient'
import { getKV } from '@/lib/kvStorage'
import { isProductionBuild } from '@/lib/runtimePolicy'

function normalizeApiUrl(rawUrl: string | undefined): string | null {
  if (!rawUrl?.trim()) return null
  const trimmed = rawUrl.trim().replace(/\/$/, '')
  if (trimmed.startsWith('/')) {
    return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`
  }

  try {
    const parsed = new URL(trimmed)
    const path = parsed.pathname.replace(/\/$/, '')
    if (!path.endsWith('/api')) parsed.pathname = `${path}/api`
    return parsed.toString().replace(/\/$/, '')
  } catch {
    return null
  }
}

const getBackendUrls = (): string[] => {
  const hostname = window.location.hostname
  const protocol = window.location.protocol
  const urls: string[] = []
  const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
  const configuredUrl = normalizeApiUrl(env?.VITE_API_BASE_URL)

  if (configuredUrl) urls.push(configuredUrl)
  urls.push(`${window.location.origin}/api`)

  // En producción nunca intentamos localhost ni puertos alternos del navegador del usuario.
  if (!isProductionBuild()) {
    if (hostname.includes('.app.github.dev')) {
      const backendHostname = hostname.replace(/-\d+\.app\.github\.dev$/, '-8000.app.github.dev')
      urls.push(`https://${backendHostname}/api`)
    }

    urls.push(
      'http://localhost:8000/api',
      'http://127.0.0.1:8000/api',
    )

    if (hostname !== 'localhost' && hostname !== '127.0.0.1' && !hostname.includes('github.dev')) {
      urls.push(`${protocol}//${hostname}:8000/api`)
    }
  }

  return [...new Set(urls)]
}

export function BackendConnectionCheck({ onSuccess }: { onSuccess: () => void }) {
  const [status, setStatus] = useState<'checking' | 'success' | 'error'>('checking')
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [retryCount, setRetryCount] = useState(0)
  const [workingUrl, setWorkingUrl] = useState<string>('')
  const [isCodespace] = useState(() => window.location.hostname.includes('.app.github.dev'))
  const productionBuild = isProductionBuild()

  const checkConnection = async () => {
    setStatus('checking')
    setErrorMessage('')

    const urls = getBackendUrls()

    for (const apiUrl of urls) {
      try {
        const controller = new AbortController()
        const timeoutId = window.setTimeout(() => controller.abort(), 3000)

        const response = await fetch(`${apiUrl}/health`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          signal: controller.signal,
        })

        window.clearTimeout(timeoutId)

        if (response.ok) {
          setWorkingUrl(apiUrl)
          updateApiUrl(apiUrl)

          try {
            const kv = getKV()
            await kv.set('settings_use_api', true)
            await kv.set('settings_api_url', apiUrl)
          } catch (error) {
            console.error('Error al guardar configuración del backend:', error)
          }

          setStatus('success')
          window.setTimeout(() => onSuccess(), 500)
          return
        }
      } catch (error) {
        console.warn(`No se pudo conectar a ${apiUrl}:`, error)
      }
    }

    setStatus('error')
    const attemptedUrls = urls.map((url, index) => `${index + 1}. ${url}`).join('\n')
    setErrorMessage(
      productionBuild
        ? `El servidor del sistema no está disponible.\n\nURLs verificadas:\n${attemptedUrls}\n\nPor seguridad, la versión de producción no continuará con almacenamiento local. Reintenta cuando el servidor esté disponible.`
        : `No se puede conectar al backend. Se intentaron las siguientes URLs:\n\n${attemptedUrls}\n\nAsegúrate de que el servidor esté corriendo en el puerto 8000.`
    )
  }

  useEffect(() => {
    void checkConnection()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retryCount])

  const handleRetry = () => {
    setRetryCount(prev => prev + 1)
  }

  if (status === 'checking') {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-50 to-blue-50">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin text-purple-600 mx-auto" />
          <h2 className="text-xl font-semibold text-gray-700">Conectando con el backend...</h2>
          <p className="text-sm text-gray-500">Verificando conexión con el servidor...</p>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-4">
        <div className="max-w-md w-full">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Servidor no disponible</AlertTitle>
            <AlertDescription className="mt-2 space-y-3">
              <pre className="text-sm whitespace-pre-wrap">{errorMessage}</pre>

              {!productionBuild && isCodespace && (
                <div className="pt-2 bg-blue-50 p-3 rounded border border-blue-200">
                  <p className="text-sm font-semibold mb-2 text-blue-900">Pasos para Codespaces:</p>
                  <ol className="text-xs space-y-1 text-blue-800 list-decimal list-inside">
                    <li>Abre la pestaña &quot;PORTS&quot; en el panel inferior</li>
                    <li>Busca el puerto <strong>8000</strong></li>
                    <li>Click derecho → &quot;Port Visibility&quot; → &quot;Public&quot;</li>
                    <li>Haz click en &quot;Reintentar Conexión&quot;</li>
                  </ol>
                </div>
              )}

              {!productionBuild && (
                <div className="pt-2">
                  <p className="text-sm font-semibold mb-2">Para iniciar el backend:</p>
                  <code className="block bg-gray-900 text-gray-100 p-3 rounded text-xs overflow-x-auto">
                    bash ./start-backend.sh
                  </code>
                </div>
              )}

              <div className="pt-2 space-y-2">
                <Button onClick={handleRetry} variant="outline" className="w-full">
                  Reintentar Conexión
                </Button>

                {!productionBuild && (
                  <Button
                    onClick={() => {
                      console.warn('Saltando verificación de conexión en modo desarrollo')
                      onSuccess()
                    }}
                    variant="ghost"
                    className="w-full text-xs"
                  >
                    Continuar sin conexión (solo desarrollo)
                  </Button>
                )}
              </div>
            </AlertDescription>
          </Alert>
        </div>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-50 to-blue-50">
        <div className="text-center space-y-4">
          <CheckCircle className="h-12 w-12 text-green-600 mx-auto" />
          <h2 className="text-xl font-semibold text-gray-700">Conexión exitosa</h2>
          <p className="text-sm text-gray-500">Backend conectado en: {workingUrl}</p>
          <p className="text-xs text-gray-400">Cargando aplicación...</p>
        </div>
      </div>
    )
  }

  return null
}
