import { useState, useCallback } from 'react'
import { HealthChecker, autoFixIssues, type HealthCheckResult } from '@/lib/healthCheck'
import type { ProductWithStock, OrderWithItems, Profile } from '@/lib/types'

export function useHealthCheck(
  products: ProductWithStock[],
  orders: OrderWithItems[],
  profiles: Profile[]
) {
  const [result, setResult] = useState<HealthCheckResult | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  const runCheck = useCallback(async () => {
    setIsRunning(true)
    
    try {
      await new Promise(resolve => setTimeout(resolve, 500))
      
      const checker = new HealthChecker(products, orders, profiles)
      const checkResult = checker.runCheck()
      
      setResult(checkResult)
      
      return checkResult
    } finally {
      setIsRunning(false)
    }
  }, [products, orders, profiles])

  const performAutoFix = useCallback(() => {
    if (!result || result.issues.length === 0) return null

    const fixes = autoFixIssues(products, orders, profiles, result.issues)
    
    return fixes
  }, [result, products, orders, profiles])

  return {
    result,
    isRunning,
    runCheck,
    performAutoFix
  }
}
