import { useState, useEffect } from 'react'
import { useKV } from '@github/spark/hooks'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Bell, Warning, Package, CheckCircle, X, Trash } from '@phosphor-icons/react'
import type { ProductWithStock, Profile } from '@/lib/types'
import { format } from 'date-fns'

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
        return 'Reabastecimiento Necesario'
    }
  }

  const getNotificationMessage = (notification: Notification) => {
    switch (notification.type) {
      case 'out_of_stock':
        return `${notification.productName} está agotado`
      case 'low_stock':
        return `${notification.productName} tiene ${notification.currentStock} unidad${notification.currentStock !== 1 ? 'es' : ''} (umbral: ${notification.threshold})`
      case 'restock_needed':
        return `Se recomienda reabastecer ${notification.productName}`
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" data-notification-trigger>
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
      <PopoverContent className="w-80 p-0" align="end">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">Notificaciones</h3>
          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={markAllAsRead}
                className="text-xs h-7"
              >
                <CheckCircle size={14} className="mr-1" />
                Marcar todo
              </Button>
            )}
            {(notifications ?? []).length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAll}
                className="text-xs h-7"
              >
                <Trash size={14} className="mr-1" />
                Limpiar
              </Button>
            )}
          </div>
        </div>

        <ScrollArea className="h-[400px]">
          {(notifications ?? []).length === 0 ? (
            <div className="text-center py-12 px-4">
              <Bell size={48} className="mx-auto text-muted-foreground mb-3" weight="duotone" />
              <p className="text-sm text-muted-foreground">
                No hay notificaciones
              </p>
            </div>
          ) : (
            <div className="p-2 space-y-2">
              {(notifications ?? []).map(notification => (
                <Card
                  key={notification.id}
                  className={`p-3 ${notification.read ? 'bg-muted/30' : 'bg-background'}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {getNotificationIcon(notification.type)}
                    </div>
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="text-sm font-semibold">
                          {getNotificationTitle(notification)}
                        </h4>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-5 w-5 -mt-1"
                          onClick={() => deleteNotification(notification.id)}
                        >
                          <X size={14} />
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {getNotificationMessage(notification)}
                      </p>
                      <div className="flex items-center justify-between">
                        <Badge variant="outline" className="text-xs">
                          {notification.profileName}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {format(new Date(notification.timestamp), 'HH:mm')}
                        </span>
                      </div>
                      {!notification.read && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => markAsRead(notification.id)}
                          className="text-xs h-6 mt-1"
                        >
                          Marcar como leído
                        </Button>
                      )}
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
