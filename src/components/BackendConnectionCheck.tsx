import { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { updateApiUrl } from '@/lib/apiClient'
import { getKV } from '@/lib/kvStorage'

// Detectar la URL correcta del backend según el entorno
const getBackendUrls = (): string[] => {
  const hostname = window.location.hostname
  const protocol = window.location.protocol
  const urls: string[] = []

  urls.push(`${window.location.origin}/api`)
  
  // Si estamos en un Codespace de GitHub
  if (hostname.includes('.app.github.dev')) {
    // Patrón: xxx-PUERTO_FRONTEND.app.github.dev -> xxx-PUERTO_BACKEND.app.github.dev
    // Ejemplo: bookish-train-xxx-5001.app.github.dev -> bookish-train-xxx-8000.app.github.dev
    
    // Reemplazar el puerto del frontend (cualquier número) por 8000
    const backendHostname = hostname.replace(/-\d+\.app\.github\.dev$/, '-8000.app.github.dev')
    urls.push(`https://${backendHostname}/api`)
    
    console.log(`🔍 Codespace detectado. Frontend: ${hostname}, Backend: ${backendHostname}`)
  }
  
  // URLs para desarrollo local
  urls.push(
    'http://localhost:8000/api',
    'http://127.0.0.1:8000/api',
  )
  
  // Si el hostname no es localhost, probarlo también (para otros entornos)
  if (hostname !== 'localhost' && hostname !== '127.0.0.1' && !hostname.includes('github.dev')) {
    urls.push(`${protocol}//${hostname}:8000/api`)
  }
  
  return urls
}

export function BackendConnectionCheck({ onSuccess }: { onSuccess: () => void }) {
  const [status, setStatus] = useState<'checking' | 'success' | 'error'>('checking')
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [retryCount, setRetryCount] = useState(0)
  const [workingUrl, setWorkingUrl] = useState<string>('')
  const [isCodespace] = useState(() => window.location.hostname.includes('.app.github.dev'))

  const checkConnection = async () => {
    setStatus('checking')
    setErrorMessage('')
    
    const urls = getBackendUrls()
    
    // Intentar cada URL en secuencia con timeout corto
    for (const apiUrl of urls) {
      try {
        console.log(`🔍 Intentando conectar a: ${apiUrl}/health`)
        
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 3000) // 3 segundos timeout
        
        const response = await fetch(`${apiUrl}/health`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          signal: controller.signal,
        })
        
        clearTimeout(timeoutId)

        if (response.ok) {
          console.log(`✅ Conexión exitosa con: ${apiUrl}`)
          setWorkingUrl(apiUrl)
          
          // Guardar la URL que funcionó usando la función optimizada
          updateApiUrl(apiUrl)
          
          // Habilitar automáticamente el modo API cuando se conecta exitosamente
          try {
            const kv = getKV()
            await kv.set('settings_use_api', true)
            await kv.set('settings_api_url', apiUrl)
            console.log('✅ Modo API habilitado automáticamente')
          } catch (error) {
            console.error('Error al habilitar modo API:', error)
          }
          
          setStatus('success')
          setTimeout(() => {
            onSuccess()
          }, 500)
          return // Salir si encontramos una URL que funciona
        }
      } catch (error) {
        console.warn(`❌ No se pudo conectar a ${apiUrl}:`, error)
        // Continuar con la siguiente URL
        continue
      }
    }
    
    // Si llegamos aquí, ninguna URL funcionó
    setStatus('error')
    setErrorMessage(
      `No se puede conectar al backend. Se intentaron las siguientes URLs:\n\n${urls.map((u, i) => `${i + 1}. ${u}`).join('\n')}\n\n` +
      `Asegúrate de que el servidor esté corriendo en el puerto 8000.`
    )
  }

  useEffect(() => {
    checkConnection()
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
          <h2 className="text-xl font-semibold text-gray-700">
            Conectando con el backend...
          </h2>
          <p className="text-sm text-gray-500">
            Verificando conexión con el backend...
          </p>
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
            <AlertTitle>Error de Conexión</AlertTitle>
            <AlertDescription className="mt-2 space-y-3">
              <pre className="text-sm whitespace-pre-wrap">{errorMessage}</pre>
              
              {isCodespace && (
                <div className="pt-2 bg-blue-50 p-3 rounded border border-blue-200">
                  <p className="text-sm font-semibold mb-2 text-blue-900">🔓 Pasos para Codespaces:</p>
                  <ol className="text-xs space-y-1 text-blue-800 list-decimal list-inside">
                    <li>Abre la pestaña &quot;PORTS&quot; en el panel inferior</li>
                    <li>Busca el puerto <strong>8000</strong></li>
                    <li>Click derecho → &quot;Port Visibility&quot; → &quot;Public&quot;</li>
                    <li>Haz click en &quot;Reintentar Conexión&quot; abajo</li>
                  </ol>
                </div>
              )}
              
              <div className="pt-2">
                <p className="text-sm font-semibold mb-2">Para iniciar el backend:</p>
                <code className="block bg-gray-900 text-gray-100 p-3 rounded text-xs overflow-x-auto">
                  bash /workspaces/spark-template/run-backend-direct.sh
                </code>
              </div>
              <div className="pt-2 space-y-2">
                <Button 
                  onClick={handleRetry} 
                  variant="outline" 
                  className="w-full"
                >
                  Reintentar Conexión
                </Button>
                <Button 
                  onClick={() => {
                    console.warn('⚠️  Saltando verificación de conexión - modo debug')
                    onSuccess()
                  }} 
                  variant="ghost" 
                  className="w-full text-xs"
                >
                  Continuar sin conexión (Debug)
                </Button>
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
          <h2 className="text-xl font-semibold text-gray-700">
            Conexión exitosa
          </h2>
          <p className="text-sm text-gray-500">
            Backend conectado en: {workingUrl}
          </p>
          <p className="text-xs text-gray-400">
            Cargando aplicación...
          </p>
        </div>
      </div>
    )
  }

  return null
}
