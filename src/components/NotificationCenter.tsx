import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Bell, Warning, Package, X, CheckCircle, TrendDown, Lightbulb } from '@phosphor-icons/react'
import type { ProductWithStock, Profile, OrderWithItems } from '@/lib/types'
import { useKV } from '@github/spark/hooks'

interface Notification {
  id: string
  type: 'low_stock' | 'out_of_stock' | 'restock_needed' | 'optimization_score'
  productName?: string
  profileName: string
  currentStock?: number
  threshold: number
  timestamp: number
  score?: number
  previousScore?: number
  trend?: 'declining' | 'stable' | 'improving'
}

interface NotificationCenterProps {
  products: ProductWithStock[]
  profiles: Profile[]
  orders?: OrderWithItems[]
  onOpenOptimization?: () => void
}

function calculateSimpleOptimizationScore(products: ProductWithStock[], orders: OrderWithItems[]): number {
  const activeProducts = products.filter(p => p.activo)
  if (activeProducts.length === 0) return 100

  let score = 0
  
  const lowStockCount = activeProducts.filter(p => p.stock_disponible < 5).length
  const stockHealthScore = Math.max(0, 100 - (lowStockCount / activeProducts.length) * 100)
  score += stockHealthScore * 0.4
  
  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
  const recentOrders = orders.filter(o => new Date(o.created_at) >= thirtyDaysAgo)
  const salesVelocityScore = Math.min(100, (recentOrders.length / activeProducts.length) * 20)
  score += salesVelocityScore * 0.3

  score += 70 * 0.15
  score += 75 * 0.10
  score += 80 * 0.05

  return Math.round(score)
}

export function NotificationCenter({ products, profiles, orders = [], onOpenOptimization }: NotificationCenterProps) {
  const [notifications, setNotifications] = useKV<Notification[]>('notifications', [])
  const [dismissedIds, setDismissedIds] = useKV<string[]>('dismissed-notifications', [])
  const [open, setOpen] = useState(false)
  const [optimizationAlertEnabled, setOptimizationAlertEnabled] = useKV<boolean>(
    'optimization-alerts-enabled',
    true
  )
  const [optimizationThreshold, setOptimizationThreshold] = useKV<number>(
    'optimization-threshold',
    70
  )
  const [lastOptimizationCheck, setLastOptimizationCheck] = useKV<number>(
    'last-optimization-check',
    0
  )
  const [lastOptimizationScore, setLastOptimizationScore] = useKV<number>(
    'last-optimization-score',
    0
  )

  useEffect(() => {
    const newNotifications: Notification[] = []

    products.forEach(product => {
      const profile = profiles.find(p => p.id === product.profile_id)
      if (!profile || !profile.active) return

      const threshold = profile.settings?.lowStockThreshold ?? 10
      const notifId = `${product.id}-${product.stock_disponible}`

      if ((dismissedIds ?? []).includes(notifId)) return

      if (product.stock_disponible === 0 && product.activo) {
        newNotifications.push({
          id: notifId,
          type: 'out_of_stock',
          productName: product.nombre,
          profileName: profile.name,
          currentStock: 0,
          threshold,
          timestamp: Date.now()
        })
      } else if (product.stock_disponible <= threshold && product.stock_disponible > 0 && product.activo) {
        newNotifications.push({
          id: notifId,
          type: 'low_stock',
          productName: product.nombre,
          profileName: profile.name,
          currentStock: product.stock_disponible,
          threshold,
          timestamp: Date.now()
        })
      }
    })

    const now = Date.now()
    const hoursSinceLastCheck = (now - (lastOptimizationCheck ?? 0)) / (1000 * 60 * 60)
    
    if (optimizationAlertEnabled && hoursSinceLastCheck >= 1) {
      profiles.filter(p => p.active).forEach(profile => {
        const profileProducts = products.filter(p => p.profile_id === profile.id)
        const profileOrders = orders.filter(o => o.profile_id === profile.id)
        
        if (profileProducts.length > 0) {
          const currentScore = calculateSimpleOptimizationScore(profileProducts, profileOrders)
          const threshold = optimizationThreshold ?? 70
          
          if (currentScore < threshold) {
            const notifId = `opt-${profile.id}-${Math.floor(now / (1000 * 60 * 60 * 24))}`
            
            if (!(dismissedIds ?? []).includes(notifId)) {
              let trend: 'declining' | 'stable' | 'improving' = 'stable'
              const previousScore = lastOptimizationScore ?? currentScore
              
              if (currentScore < previousScore - 5) {
                trend = 'declining'
              } else if (currentScore > previousScore + 5) {
                trend = 'improving'
              }
              
              newNotifications.push({
                id: notifId,
                type: 'optimization_score',
                profileName: profile.name,
                threshold,
                timestamp: now,
                score: currentScore,
                previousScore,
                trend
              })
            }
          }
          
          setLastOptimizationScore(currentScore)
        }
      })
      
      setLastOptimizationCheck(now)
    }

    setNotifications(newNotifications)
  }, [products, profiles, orders, dismissedIds, optimizationAlertEnabled, optimizationThreshold, setNotifications])

  const activeNotifications = (notifications ?? []).filter(n => !(dismissedIds ?? []).includes(n.id))

  const dismissNotification = (id: string) => {
    setDismissedIds(current => [...(current ?? []), id])
  }

  const clearAll = () => {
    setDismissedIds(current => [...(current ?? []), ...activeNotifications.map(n => n.id)])
  }

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'out_of_stock':
        return <X size={18} weight="bold" className="text-destructive" />
      case 'low_stock':
        return <Warning size={18} weight="bold" className="text-warning" />
      case 'optimization_score':
        return <TrendDown size={18} weight="bold" className="text-accent" />
      default:
        return <Package size={18} weight="bold" className="text-accent" />
    }
  }

  const getNotificationMessage = (notif: Notification) => {
    switch (notif.type) {
      case 'out_of_stock':
        return 'Sin stock disponible'
      case 'low_stock':
        return `Stock bajo: ${notif.currentStock} unidades`
      case 'optimization_score':
        const trendText = notif.trend === 'declining' ? '📉 Bajando' : notif.trend === 'improving' ? '📈 Mejorando' : '→ Estable'
        return `Score de optimización: ${notif.score}/100 ${trendText}`
      default:
        return 'Actualización de stock'
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative hover:bg-primary/10"
          data-notification-trigger
        >
          <Bell size={20} />
          {activeNotifications.length > 0 && (
            <Badge 
              variant="destructive" 
              className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs rounded-full animate-pulse-glow"
            >
              {activeNotifications.length}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h3 className="font-semibold">Notificaciones</h3>
          {activeNotifications.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAll}
              className="text-xs"
            >
              <CheckCircle size={14} className="mr-1" />
              Limpiar todo
            </Button>
          )}
        </div>

        <ScrollArea className="h-[300px]">
          {activeNotifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Bell size={48} className="text-muted-foreground mb-2" weight="duotone" />
              <p className="text-sm text-muted-foreground">No hay notificaciones</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {activeNotifications.map(notif => (
                <div
                  key={notif.id}
                  className={`p-4 hover:bg-muted/50 transition-colors group ${
                    notif.type === 'optimization_score' ? 'cursor-pointer' : ''
                  }`}
                  onClick={() => {
                    if (notif.type === 'optimization_score' && onOpenOptimization) {
                      onOpenOptimization()
                      setOpen(false)
                    }
                  }}
                >
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 mt-1">
                      {getNotificationIcon(notif.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      {notif.productName && (
                        <p className="text-sm font-medium truncate">{notif.productName}</p>
                      )}
                      <p className="text-xs text-muted-foreground">{notif.profileName}</p>
                      <p className="text-xs mt-1">{getNotificationMessage(notif)}</p>
                      {notif.type === 'optimization_score' && notif.score !== undefined && notif.score < (notif.threshold ?? 70) && (
                        <div className="flex items-center gap-1 mt-2 text-xs text-accent">
                          <Lightbulb size={12} weight="fill" />
                          <span>Toca para ver detalles</span>
                        </div>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="flex-shrink-0 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation()
                        dismissNotification(notif.id)
                      }}
                    >
                      <X size={14} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  )
}
