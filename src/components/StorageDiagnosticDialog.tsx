import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Database, CheckCircle, XCircle, Download, Upload, Trash } from '@phosphor-icons/react'
import { getKV } from '@/lib/kvStorage'
import { exportAllData, clearAllData, importAllData } from '@/lib/dataInitializer'
import { toast } from 'sonner'

export function StorageDiagnosticDialog() {
  const [isOpen, setIsOpen] = useState(false)
  const [storageType, setStorageType] = useState<'spark' | 'localStorage'>('localStorage')
  const [dataStats, setDataStats] = useState({
    profiles: 0,
    products: 0,
    stock: 0,
    orders: 0,
    orderItems: 0
  })

  useEffect(() => {
    if (isOpen) {
      checkStorageType()
      loadDataStats()
    }
  }, [isOpen])

  const checkStorageType = () => {
    if (typeof window !== 'undefined' && window.spark?.kv) {
      const kv = window.spark.kv
      if (typeof kv.get === 'function' && 
          typeof kv.set === 'function' && 
          typeof kv.delete === 'function' && 
          typeof kv.keys === 'function') {
        setStorageType('spark')
        return
      }
    }
    setStorageType('localStorage')
  }

  const loadDataStats = async () => {
    try {
      const kv = getKV()
      const [profiles, products, stock, orders, orderItems] = await Promise.all([
        kv.get<any[]>('inventory-profiles'),
        kv.get<any[]>('inventory-products'),
        kv.get<any[]>('inventory-stock'),
        kv.get<any[]>('inventory-orders'),
        kv.get<any[]>('inventory-order-items')
      ])

      setDataStats({
        profiles: profiles?.length || 0,
        products: products?.length || 0,
        stock: stock?.length || 0,
        orders: orders?.length || 0,
        orderItems: orderItems?.length || 0
      })
    } catch (error) {
      console.error('Error loading data stats:', error)
      toast.error('Error al cargar estadísticas de datos')
    }
  }

  const handleExport = async () => {
    try {
      const data = await exportAllData()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `inventory-backup-${new Date().toISOString()}.json`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Datos exportados exitosamente')
    } catch (error) {
      console.error('Error exporting data:', error)
      toast.error('Error al exportar datos')
    }
  }

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'application/json'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return

      try {
        const text = await file.text()
        const data = JSON.parse(text)
        await importAllData(data)
        await loadDataStats()
        toast.success('Datos importados exitosamente')
      } catch (error) {
        console.error('Error importing data:', error)
        toast.error('Error al importar datos')
      }
    }
    input.click()
  }

  const handleClear = async () => {
    if (!confirm('¿Estás seguro? Esto eliminará TODOS los datos del sistema.')) {
      return
    }

    try {
      await clearAllData()
      await loadDataStats()
      toast.success('Todos los datos fueron eliminados')
    } catch (error) {
      console.error('Error clearing data:', error)
      toast.error('Error al limpiar datos')
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Database className="h-4 w-4 mr-2" />
          Diagnóstico
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Diagnóstico de Almacenamiento</DialogTitle>
          <DialogDescription>
            Información sobre el sistema de almacenamiento y datos
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Storage Type */}
          <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 rounded-lg">
            <div className="flex items-center gap-2">
              {storageType === 'spark' ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-yellow-500" />
              )}
              <span className="font-medium">Sistema de Almacenamiento</span>
            </div>
            <Badge variant={storageType === 'spark' ? 'default' : 'secondary'}>
              {storageType === 'spark' ? 'Spark KV' : 'localStorage (fallback)'}
            </Badge>
          </div>

          {/* Data Statistics */}
          <div className="space-y-2">
            <h3 className="font-semibold text-sm">Estadísticas de Datos</h3>
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2 bg-slate-50 dark:bg-slate-900 rounded">
                <div className="text-xs text-slate-500">Perfiles</div>
                <div className="text-lg font-bold">{dataStats.profiles}</div>
              </div>
              <div className="p-2 bg-slate-50 dark:bg-slate-900 rounded">
                <div className="text-xs text-slate-500">Productos</div>
                <div className="text-lg font-bold">{dataStats.products}</div>
              </div>
              <div className="p-2 bg-slate-50 dark:bg-slate-900 rounded">
                <div className="text-xs text-slate-500">Stock</div>
                <div className="text-lg font-bold">{dataStats.stock}</div>
              </div>
              <div className="p-2 bg-slate-50 dark:bg-slate-900 rounded">
                <div className="text-xs text-slate-500">Pedidos</div>
                <div className="text-lg font-bold">{dataStats.orders}</div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <h3 className="font-semibold text-sm">Acciones</h3>
            <div className="flex gap-2">
              <Button onClick={handleExport} variant="outline" size="sm" className="flex-1">
                <Download className="h-4 w-4 mr-2" />
                Exportar
              </Button>
              <Button onClick={handleImport} variant="outline" size="sm" className="flex-1">
                <Upload className="h-4 w-4 mr-2" />
                Importar
              </Button>
              <Button onClick={handleClear} variant="destructive" size="sm">
                <Trash className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Storage Info */}
          <div className="text-xs text-slate-500 space-y-1">
            <p>• Spark KV: Almacenamiento nativo de GitHub Spark</p>
            <p>• localStorage: Fallback automático si Spark KV no está disponible</p>
            <p>• Los datos persisten en el navegador</p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
