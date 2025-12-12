import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { ClockCounterClockwise } from '@phosphor-icons/react'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { IMEIHistoryDialog } from './IMEIHistoryDialog'

interface IMEIListDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  productId: number
  productName: string
  locationId?: number
}

export function IMEIListDialog({ open, onOpenChange, productId, productName, locationId }: IMEIListDialogProps) {
  const [imeis, setImeis] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedImei, setSelectedImei] = useState<string | null>(null)

  useEffect(() => {
    const loadImeis = async () => {
      if (!locationId) return
      setLoading(true)
      try {
        const data = await inventoryServiceInstance.getAvailableIMEIs(productId, locationId)
        setImeis(data)
      } catch (error) {
        console.error('Error loading IMEIs:', error)
      } finally {
        setLoading(false)
      }
    }

    if (open && productId && locationId) {
      loadImeis()
    }
  }, [open, productId, locationId])

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>IMEIs Disponibles: {productName}</DialogTitle>
          </DialogHeader>
          
          <div className="mt-4 max-h-[60vh] overflow-y-auto">
            {loading ? (
              <div className="text-center py-4">Cargando IMEIs...</div>
            ) : imeis.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground">
                No hay IMEIs disponibles en esta ubicación.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>IMEI</TableHead>
                    <TableHead className="w-[100px]">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {imeis.map((imei) => (
                    <TableRow key={imei}>
                      <TableCell className="font-mono">{imei}</TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedImei(imei)}
                          title="Ver historial"
                        >
                          <ClockCounterClockwise size={16} />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {selectedImei && (
        <IMEIHistoryDialog
          open={!!selectedImei}
          onOpenChange={(open) => !open && setSelectedImei(null)}
          imei={selectedImei}
        />
      )}
    </>
  )
}
