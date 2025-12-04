import { useState, useEffect } from 'react'
import { useKV } from '@github/spark/hooks'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Bell, Warning, Package, X } from '@phosphor-icons/react'
import { format } from 'date-fns'
import type { ProductWithStock, Profile } from '@/lib/types'

export interface Notification {
  id: string
  type: 'low_stock' | 'out_of_stock' | 'restock_needed'
  productId: number
  productName: string
  profileId: number
  profileName: string
  currentStock: number
  threshold: number
  timestamp: string
  read: boolean
}

interface NotificationCenterProps {
  products: ProductWithStock[]
  profiles: Profile[]
}

export function NotificationCenter({ products, profiles }: NotificationCenterProps) {
  const [notifications, setNotifications] = useKV<Notification[]>('inventory-notifications', [])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    checkStockLevels()
  }, [products, profiles])

  const checkStockLevels = () => {
    const newNotifications: Notification[] = []
    const now = new Date().toISOString()

    profiles.forEach(profile => {
      if (!profile.active || !profile.settings?.enableNotifications) return

      const threshold = profile.settings.lowStockThreshold || 5
      const profileProducts = products.filter(p => p.profile_id === profile.id && p.activo)

      profileProducts.forEach(product => {
        const existingNotification = (notifications ?? []).find(
          n => n.productId === product.id && !n.read
        )

        if (product.stock_disponible === 0 && !existingNotification) {
          newNotifications.push({
            id: `${product.id}-out-${Date.now()}`,
            type: 'out_of_stock',
            productId: product.id,
            productName: product.nombre,
            profileId: profile.id,
            profileName: profile.name,
            currentStock: 0,
            threshold,
            timestamp: now,
            read: false
          })
        } else if (product.stock_disponible <= threshold && product.stock_disponible > 0 && !existingNotification) {
          newNotifications.push({
            id: `${product.id}-low-${Date.now()}`,
            type: 'low_stock',
            productId: product.id,
            productName: product.nombre,
            profileId: profile.id,
            profileName: profile.name,
            currentStock: product.stock_disponible,
            threshold,
            timestamp: now,
            read: false
          })
        }
      })
    })

    if (newNotifications.length > 0) {
      setNotifications(current => [...newNotifications, ...(current ?? [])])
    }
  }

  const unreadCount = (notifications ?? []).filter(n => !n.read).length

  const markAsRead = (notificationId: string) => {
    setNotifications(current =>
      (current ?? []).map(n =>
        n.id === notificationId ? { ...n, read: true } : n
      )
    )
  }

  const markAllAsRead = () => {
    setNotifications(current =>
      (current ?? []).map(n => ({ ...n, read: true }))
    )
  }

  const deleteNotification = (notificationId: string) => {
    setNotifications(current =>
      (current ?? []).filter(n => n.id !== notificationId)
    )
  }

  const clearAll = () => {
    setNotifications([])
  }

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'out_of_stock':
        return <Warning size={18} weight="fill" className="text-destructive" />
      case 'low_stock':
        return <Warning size={18} weight="fill" className="text-yellow-500" />
      case 'restock_needed':
        return <Package size={18} weight="duotone" className="text-blue-500" />
    }
  }

  const getNotificationTitle = (notification: Notification) => {
    switch (notification.type) {
      case 'out_of_stock':
        return 'Sin Stock'
      case 'low_stock':
        return 'Stock Bajo'
      case 'restock_needed':
        return 'Se recomienda reabastecer'
    }
  }

  const getNotificationMessage = (notification: Notification) => {
    switch (notification.type) {
      case 'out_of_stock':
        return `${notification.productName} está agotado`
      case 'low_stock':
        return `${notification.productName} tiene solo ${notification.currentStock} unidades (umbral: ${notification.threshold})`
      case 'restock_needed':
        return `${notification.productName} necesita reabastecimiento`
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          data-notification-trigger
        >
          <Bell size={20} />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-96 p-0" align="end">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">Notificaciones</h3>
            {unreadCount > 0 && (
              <Badge variant="secondary">{unreadCount} nueva{unreadCount !== 1 ? 's' : ''}</Badge>
            )}
          </div>
          <div className="flex gap-1">
            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={markAllAsRead}
              >
                Marcar todas
              </Button>
            )}
            {notifications && notifications.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAll}
              >
                Limpiar
              </Button>
            )}
          </div>
        </div>
        <ScrollArea className="h-[400px]">
          {!notifications || notifications.length === 0 ? (
            <div className="text-center py-12 px-4">
              <Bell size={48} className="mx-auto text-muted-foreground mb-3" weight="duotone" />
              <p className="text-sm text-muted-foreground">
                No hay notificaciones
              </p>
            </div>
          ) : (
            <div className="p-2 space-y-2">
              {notifications.map(notification => (
                <Card
                  key={notification.id}
                  className={`p-3 cursor-pointer transition-colors hover:bg-accent/50 ${
                    !notification.read ? 'border-primary' : ''
                  }`}
                  onClick={() => markAsRead(notification.id)}
                >
                  <div className="flex gap-3">
                    <div className="mt-0.5">
                      {getNotificationIcon(notification.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <p className="font-medium text-sm">
                            {getNotificationTitle(notification)}
                          </p>
                          <p className="text-sm text-muted-foreground mt-0.5">
                            {getNotificationMessage(notification)}
                          </p>
                          <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                            <Badge variant="outline" className="text-xs">
                              {notification.profileName}
                            </Badge>
                            <span>•</span>
                            <span>{format(new Date(notification.timestamp), 'dd/MM/yyyy HH:mm')}</span>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 shrink-0"
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteNotification(notification.id)
                          }}
                        >
                          <X size={14} />
                        </Button>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  )
}
