import { useEffect, useState } from 'react'
// import { initialProfiles, initialProducts, initialStock, initialOrders, initialOrderItems } from '@/lib/initialData'

export function useInitializeData() {
  const [isInitialized, setIsInitialized] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const initialize = async () => {
      try {
        // V2.0: No inicializar datos de ejemplo automáticamente
        // Permitir que el usuario empiece de cero
        setIsInitialized(true)
      } catch (error) {
        console.error('Error initializing data:', error)
        setIsInitialized(true)
      } finally {
        setIsLoading(false)
      }
    }

    initialize()
  }, [])

  return { isInitialized, isLoading }
}
