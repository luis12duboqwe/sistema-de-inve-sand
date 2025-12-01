import { useEffect, useState } from 'react'
import { inventoryService } from '@/lib/inventoryService'
import { initialProfiles, initialProducts, initialStock, initialOrders, initialOrderItems } from '@/lib/initialData'

export function useInitializeData() {
  const [isInitialized, setIsInitialized] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const initialize = async () => {
      try {
        const existingProfiles = await inventoryService.getProfiles()
        
        if (existingProfiles.length === 0) {
          await inventoryService.initializeData(
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
      } finally {
        setIsLoading(false)
      }
    }

    initialize()
  }, [])

  return { isInitialized, isLoading }
}
