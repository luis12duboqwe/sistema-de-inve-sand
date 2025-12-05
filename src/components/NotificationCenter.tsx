import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Popover, PopoverContent, PopoverTr
import { Bell, Warning, Package, X } from '@pho
import type { ProductWithStock, Profile } from '@/lib/types'

  id: string
  productName: string
import type { ProductWithStock, Profile } from '@/lib/types'
import { useKV } from '@github/spark/hooks'

interface Notification {
  id: string
  type: 'low_stock' | 'out_of_stock' | 'restock_needed'
  productName: string
  profileName: string
  profiles: Profile

  const [notificati

 

    const now = new Date().toISOStr

      if (!profile.ac
 

        const existingNotification = (notifications ?? []).find(
        )
        if (product.stock_disponible === 

            product
            threshold,
            timestamp: now

          newNotifications.push({
            type: 'low_stock',
            profileName: profile.name,

            read: false
        }

    if (newNotifications.length > 0) {
    }

    setNotifications(current => 
        n.id === notificationId ? { ...n, read: true } : n
    )


    )

    setNotifications(current => 
    )

    setNotifications([])


    switch (type) {
        return <Warning
        retu
        return <Package size={18} weight="duotone" className="text-primary" />
  }
  const getNotificationTitle = (notification: 
            type: 'low_stock',
            productName: product.nombre,
            profileName: profile.name,
            threshold,
            currentStock: product.stock_disponible,
            timestamp: now,
            read: false
          })
        }
      })
    })

    if (newNotifications.length > 0) {
      setNotifications(current => [...(current ?? []), ...newNotifications])
    }
  }

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

  const unreadCount = (notifications ?? []).filter(n => !n.read).length

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'out_of_stock':
        return <Warning size={18} weight="fill" className="text-destructive" />
      case 'low_stock':
        return <Warning size={18} weight="duotone" className="text-yellow-500" />
      case 'restock_needed':
        return <Package size={18} weight="duotone" className="text-primary" />
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

              </Button>
          </div>

          {!notifications || notifications.length === 0 ?
              <Bell siz
                No hay notificaciones
            </div>
            <div className="p-2 space-y-2">
     
   

          
                    <div className="shrink-0 mt-
                    </div>
               
                         
                     
                            {g
                          <div clas
         
                            
                          </div
                  
                          size="ico
                          onClick={(e) => {
             
                        >
                    
            
                <
            </div>

    </Popover>
}


























































































