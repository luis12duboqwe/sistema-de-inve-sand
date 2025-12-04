import { useState, useEffect } from 'react'
import { useKV } from '@github/spark/hooks'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/s
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Popover,
import { Bell, Wa
import { format }
export interface Notification {
  type: 'low_stock' | 'out_of_stock' | 'restock_needed'
  productName: string
  profileName: string

  read: boolean
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
        return 'Stock B
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
        return `Se recomien
  }
  return (
     
   

              className="absolute -top-1 -right-1 h-5 w-5 p-0 flex
              {unreadCount > 9 ?
          )}
      </PopoverTrigger>
        <div className=
          <div className="flex items-center gap-2">
              <Button
                size="sm"
     
   

          
                variant="ghost"
                onClick={clear
              >
                Limpiar
            )}
        </div>
        <ScrollArea className="h-[4
            <div className="text-center py-12 px-4">
             
              </p>
          ) : (
            
                 
                >
                    <div className="mt-0.5">
                    </div>
                      <div className="flex items-start just
                          {getNotificationTitle(not
                        <Button
                     
                          onCli
                         
                      </div>
                        {getNotificatio
               
                          {notification.profileName}
                        <sp
                       
              
                          variant="ghost"
                     
                        >
                        <
                    </div>
                </Card>
            </d
        </ScrollArea>
    </Popover>
}





































































