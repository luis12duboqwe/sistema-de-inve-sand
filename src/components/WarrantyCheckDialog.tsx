import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { WarrantyStatus } from '@/lib/types'
import { toast } from 'sonner'
import { ShieldCheck, ShieldWarning, Calendar, Tag } from '@phosphor-icons/react'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'

interface WarrantyCheckDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WarrantyCheckDialog({ open, onOpenChange }: WarrantyCheckDialogProps) {
  const [imei, setImei] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<WarrantyStatus | null>(null)

  const handleCheck = async () => {
    if (!imei.trim()) return

    setLoading(true)
    setResult(null)
    try {
      const status = await inventoryServiceInstance.checkWarrantyStatus(imei)
      setResult(status)
    } catch (error) {
      console.error('Error checking warranty:', error)
      toast.error('Error al verificar garantía. Verifique el IMEI e intente nuevamente.')
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'vigente':
        return <Badge className="bg-green-500 hover:bg-green-600">Vigente</Badge>
      case 'vencida':
        return <Badge variant="destructive">Vencida</Badge>
      case 'sin_garantia':
        return <Badge variant="secondary">Sin Garantía</Badge>
      case 'en_stock':
        return <Badge variant="outline">En Stock (No vendido)</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A'
    try {
      return format(new Date(dateStr), 'dd MMM yyyy', { locale: es })
    } catch {
      return dateStr
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5" />
            Verificar Garantía
          </DialogTitle>
          <DialogDescription>
            Ingrese el IMEI del dispositivo para consultar el estado de su garantía.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="flex gap-2">
            <div className="grid w-full items-center gap-1.5">
              <Label htmlFor="imei">IMEI</Label>
              <Input
                id="imei"
                placeholder="Ingrese IMEI..."
                value={imei}
                onChange={(e) => setImei(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
              />
            </div>
            <Button 
              className="mt-auto" 
              onClick={handleCheck}
              disabled={loading || !imei.trim()}
            >
              {loading ? 'Verificando...' : 'Verificar'}
            </Button>
          </div>

          {result && (
            <Card className="p-4 mt-2 border-l-4 border-l-primary">
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-lg">{result.product || 'Producto Desconocido'}</h3>
                    <p className="text-sm text-muted-foreground">IMEI: {result.imei}</p>
                  </div>
                  {getStatusBadge(result.status)}
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="space-y-1">
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      <span>Fecha Venta</span>
                    </div>
                    <p className="font-medium">{formatDate(result.sale_date)}</p>
                  </div>
                  
                  <div className="space-y-1">
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <ShieldWarning className="h-4 w-4" />
                      <span>Vence</span>
                    </div>
                    <p className="font-medium">{formatDate(result.expiration_date)}</p>
                  </div>
                </div>

                {result.days_remaining !== undefined && result.days_remaining > 0 && (
                  <div className="bg-blue-50 text-blue-700 px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2">
                    <Tag className="h-4 w-4" />
                    Quedan {result.days_remaining} días de garantía
                  </div>
                )}

                <div className="text-sm text-muted-foreground bg-muted/50 p-2 rounded">
                  {result.detail}
                </div>
              </div>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
