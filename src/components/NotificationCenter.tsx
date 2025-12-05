import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badg
import { Badge } from '@/components/ui/badge'
import {
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
} from '
import { f
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Bell, Warning, Package, X } from '@phosphor-icons/react'
import { format } from 'date-fns'
import type { ProductWithStock, Profile } from '@/lib/types'

  threshold: number
  profiles: 

  const [notificati

    checkStockLevel

    const newNotificat

      if (!profile.
      const thr


        )
        if (product.stock_disp
            id: `${pr
 

            currentStock: 0,
            timestamp: now,
          })

            type: '
            productNam
            profileName: p

            read: false
        }
    })

    }


    setNotifications(current =>
        n.id === notificationId ? { ...n, read: true } : n


    setNotifications(current =>
    )


    )

    setNotifications([])

    switch (type) {
        return <Warning size={18} weight
        return <Warning size={18} 
        return <Package size={18} weig
  }
  const getNotificatio
      case 'out_of_stock':
      case 'low_stock':
      case '
    }

    switch (notification.type) {
        return `${notification
        return `${notification.pro
        return `${notification.productNa
  }
  return (
      <PopoverTrigger asChild>
          variant="gho
          className="relati
        >
          {u
         
        
      

      <PopoverContent className="w-96 
          <div className="flex items-center gap-2">
     
   

              <Button

              >
              </Button>
            {notifications && 
                variant="ghost"
       
     
   

          {!notifications || no
              <Bell size={48} c
                No hay notificaciones
     
   

                  className={`p-3 cursor-pointer transitio
                  }`}
                >
     
   

                          
                        
   

                              {notification.profileName}
                   
                          
                        <Button
      case 'low_stock':
                          onClick={(e) => {
                            
                        >
     
   

            </div>
        </ScrollArea>
    </Popover>
}

        return 'Stock Bajo'
      case 'restock_needed':
        return 'Se recomienda reabastecer'
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

        </Button>

      <PopoverContent className="w-96 p-0" align="end">
        <div className="flex items-center justify-between p-4 border-b">

            <h3 className="font-semibold">Notificaciones</h3>
            {unreadCount > 0 && (
              <Badge variant="secondary">{unreadCount} nueva{unreadCount !== 1 ? 's' : ''}</Badge>
            )}
          </div>
          <div className="flex gap-1">
            {unreadCount > 0 && (

                variant="ghost"

                onClick={markAllAsRead}
              >
                Marcar todas
              </Button>
            )}
            {notifications && notifications.length > 0 && (
              <Button

                size="sm"
                onClick={clearAll}


              </Button>

          </div>

        <ScrollArea className="h-[400px]">
          {!notifications || notifications.length === 0 ? (

              <Bell size={48} className="mx-auto text-muted-foreground mb-3" weight="duotone" />
              <p className="text-sm text-muted-foreground">
                No hay notificaciones

            </div>

            <div className="p-2 space-y-2">
              {notifications.map(notification => (
                <Card
                  key={notification.id}
                  className={`p-3 cursor-pointer transition-colors hover:bg-accent/50 ${
                    !notification.read ? 'border-primary' : ''
                  }`}
                  onClick={() => markAsRead(notification.id)}

                  <div className="flex gap-3">

                      {getNotificationIcon(notification.type)}

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


                          size="icon"
                          className="h-6 w-6 shrink-0"
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteNotification(notification.id)
                          }}

                          <X size={14} />
                        </Button>
                      </div>

                  </div>

              ))}
            </div>
          )}

      </PopoverContent>

  )

