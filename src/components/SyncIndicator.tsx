import { motion, AnimatePresence } from 'framer-motion'
import { CloudArrowUp, CloudCheck, CloudSlash, ArrowsClockwise } from '@phosphor-icons/react'
import type { SyncStatus } from '@/hooks/use-realtime-sync'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

interface SyncIndicatorProps {
  syncStatus: SyncStatus
}

export function SyncIndicator({ syncStatus }: SyncIndicatorProps) {
  const { isSyncing, lastSyncTime, syncError } = syncStatus

  const getStatusIcon = () => {
    if (syncError) {
      return <CloudSlash size={16} weight="fill" className="text-destructive" />
    }
    if (isSyncing) {
      return (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        >
          <ArrowsClockwise size={16} weight="bold" className="text-primary" />
        </motion.div>
      )
    }
    return <CloudCheck size={16} weight="fill" className="text-success" />
  }

  const getStatusText = () => {
    if (syncError) return 'Error de sincronización'
    if (isSyncing) return 'Sincronizando...'
    return 'Sincronizado'
  }

  const getTimeAgo = () => {
    if (!lastSyncTime) return 'Nunca'
    
    const now = new Date()
    const diff = now.getTime() - lastSyncTime.getTime()
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (seconds < 10) return 'justo ahora'
    if (seconds < 60) return `hace ${seconds}s`
    if (minutes < 60) return `hace ${minutes}m`
    return `hace ${hours}h`
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2 }}
          >
            <Badge 
              variant={syncError ? "destructive" : isSyncing ? "default" : "secondary"}
              className="flex items-center gap-1.5 cursor-help"
            >
              {getStatusIcon()}
              <span className="hidden sm:inline text-xs">{getStatusText()}</span>
            </Badge>
          </motion.div>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1">
            <p className="font-semibold">{getStatusText()}</p>
            {!syncError && <p className="text-xs text-muted-foreground">Última sincronización: {getTimeAgo()}</p>}
            {syncError && <p className="text-xs">{syncError}</p>}
            <p className="text-xs text-muted-foreground">Dispositivo: {syncStatus.deviceId.slice(0, 12)}...</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
