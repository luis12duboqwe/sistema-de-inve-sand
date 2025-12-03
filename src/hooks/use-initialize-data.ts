import { useEffect, useState } from 'react'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { initialProfiles, initialProducts, initialStock, initialOrders, initialOrderItems } from '@/lib/initialData'

export function useInitializeData() {
  const [isInitialized, setIsInitialized] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const initialize = async () => {
      try {
        const existingProfiles = await inventoryServiceInstance.getProfiles()
        
        if (existingProfiles.length === 0) {
          await inventoryServiceInstance.initializeData(
            initialProfiles,
            initialProducts,
            initialStock,
            initialOrders,
            initialOrderItems
          )
        }
        
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
