import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Bell, Warning, Package, X, CheckCircle } from '@phosphor-icons/react'
import type { ProductWithStock, Profile } from '@/lib/types'
import { useKV } from '@github/spark/hooks'

interface Notification {
  id: string
  type: 'low_stock' | 'out_of_stock' | 'restock_needed'
  productName: string
  profileName: string
  currentStock: number
  threshold: number
  timestamp: number
}

interface NotificationCenterProps {
  products: ProductWithStock[]
  profiles: Profile[]
}

export function NotificationCenter({ products, profiles }: NotificationCenterProps) {
  const [notifications, setNotifications] = useKV<Notification[]>('notifications', [])
  const [dismissedIds, setDismissedIds] = useKV<string[]>('dismissed-notifications', [])
  const [open, setOpen] = useState(false)

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

    setNotifications(newNotifications)
  }, [products, profiles, dismissedIds, setNotifications])

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
                  className="p-4 hover:bg-muted/50 transition-colors group"
                >
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 mt-1">
                      {getNotificationIcon(notif.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{notif.productName}</p>
                      <p className="text-xs text-muted-foreground">{notif.profileName}</p>
                      <p className="text-xs mt-1">{getNotificationMessage(notif)}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="flex-shrink-0 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => dismissNotification(notif.id)}
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
