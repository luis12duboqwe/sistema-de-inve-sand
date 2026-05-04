/**
 * Virtual scrolling hook for performance with large lists.
 * Renders only visible items, dramatically improving performance.
 */

import { useCallback } from 'react'

interface UseVirtualScrollOptions {
  itemHeight: number
  containerHeight: number
  items: unknown[]
  overscan?: number  // Extra items to render beyond visible area
}

interface VirtualScrollState {
  startIndex: number
  endIndex: number
  visibleItems: unknown[]
  offsetY: number
  totalHeight: number
}

export function useVirtualScroll({
  itemHeight,
  containerHeight,
  items,
  overscan = 3
}: UseVirtualScrollOptions): (scrollTop: number) => VirtualScrollState {
  
  const calculate = useCallback((scrollTop: number): VirtualScrollState => {
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan)
    const endIndex = Math.min(
      items.length,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
    )
    
    const visibleItems = items.slice(startIndex, endIndex)
    const offsetY = startIndex * itemHeight
    const totalHeight = items.length * itemHeight
    
    return {
      startIndex,
      endIndex,
      visibleItems,
      offsetY,
      totalHeight
    }
  }, [items, itemHeight, containerHeight, overscan])
  
  return calculate
}
