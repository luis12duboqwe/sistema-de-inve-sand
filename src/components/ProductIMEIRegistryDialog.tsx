import { useEffect, useMemo, useState } from 'react'
import { format } from 'date-fns'
import { Barcode, ClockCounterClockwise } from '@phosphor-icons/react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { ProductIMEI, ProductWithStock } from '@/lib/types'

import { IMEIHistoryDialog } from './IMEIHistoryDialog'
import { PrintButton } from './ProductLabel'

interface ProductIMEIRegistryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock
}

const formatDate = (value?: string) => {
  if (!value) return '-'
  try {
    return format(new Date(value), 'dd/MM/yyyy HH:mm')
  } catch {
    return value
  }
}

const getStatusLabel = (record: ProductIMEI) => {
  if (record.transfer_id) return 'En tránsito'
  if (record.vendido) return 'Vendido'
  return 'Disponible'
}

const getStatusClassName = (record: ProductIMEI) => {
  if (record.transfer_id) return 'bg-amber-500 text-white'
  if (record.vendido) return 'bg-blue-600 text-white'
  return 'bg-emerald-600 text-white'
}

export function ProductIMEIRegistryDialog({ open, onOpenChange, product }: ProductIMEIRegistryDialogProps) {
  const [imeiRecords, setImeiRecords] = useState<ProductIMEI[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedImei, setSelectedImei] = useState<string | null>(null)

  useEffect(() => {
    const loadImeiRecords = async () => {
      setLoading(true)
      try {
        const records = await inventoryServiceInstance.getProductIMEIs(product.id)
        setImeiRecords(records)
      } catch (error) {
        console.error('Error loading product IMEI registry:', error)
      } finally {
        setLoading(false)
      }
    }

    if (open) {
      void loadImeiRecords()
      setSearch('')
    }
  }, [open, product.id])

  const filteredRecords = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return imeiRecords

    return imeiRecords.filter(record => {
      const status = getStatusLabel(record).toLowerCase()
      return (
        record.imei.toLowerCase().includes(term) ||
        (record.location_name || '').toLowerCase().includes(term) ||
        (record.supplier_name || '').toLowerCase().includes(term) ||
        status.includes(term)
      )
    })
  }, [imeiRecords, search])

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="w-[96vw] max-w-[1500px] max-h-[92vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Barcode className="h-5 w-5" />
              Registro de IMEIs: {product.nombre}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="rounded-lg border p-3">
                <div className="text-xs text-muted-foreground">Total de IMEIs</div>
                <div className="text-2xl font-semibold">{imeiRecords.length}</div>
              </div>
              <div className="rounded-lg border p-3">
                <div className="text-xs text-muted-foreground">Disponibles</div>
                <div className="text-2xl font-semibold">{imeiRecords.filter(record => !record.vendido && !record.transfer_id).length}</div>
              </div>
              <div className="rounded-lg border p-3">
                <div className="text-xs text-muted-foreground">Vendidos / tránsito</div>
                <div className="text-2xl font-semibold">{imeiRecords.filter(record => record.vendido || record.transfer_id).length}</div>
              </div>
            </div>

            <div className="space-y-2">
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar por IMEI, ubicación, proveedor o estado..."
              />
              <p className="text-xs text-muted-foreground">
                Mostrando {filteredRecords.length} de {imeiRecords.length} registros.
              </p>
            </div>

            {loading ? (
              <div className="py-8 text-center text-muted-foreground">Cargando registro de IMEIs...</div>
            ) : filteredRecords.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">No se encontraron IMEIs para este producto.</div>
            ) : (
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>IMEI</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Ubicación</TableHead>
                      <TableHead>Ingreso</TableHead>
                      <TableHead>Proveedor</TableHead>
                      <TableHead>Tipo ingreso</TableHead>
                      <TableHead className="w-[160px]">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredRecords.map(record => (
                      <TableRow key={record.id}>
                        <TableCell className="font-mono">{record.imei}</TableCell>
                        <TableCell>
                          <Badge className={getStatusClassName(record)}>{getStatusLabel(record)}</Badge>
                        </TableCell>
                        <TableCell>{record.location_name || '-'}</TableCell>
                        <TableCell>{formatDate(record.received_at || record.created_at)}</TableCell>
                        <TableCell>{record.supplier_name || '-'}</TableCell>
                        <TableCell>{record.acquisition_type || '-'}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedImei(record.imei)}
                              title="Ver expediente"
                            >
                              <ClockCounterClockwise size={16} />
                            </Button>
                            {!record.vendido && !record.transfer_id && (
                              <PrintButton
                                product={{
                                  nombre: product.nombre,
                                  sku: product.sku,
                                  color: product.color,
                                  capacidad: product.capacidad,
                                }}
                                imei={record.imei}
                              />
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {selectedImei && (
        <IMEIHistoryDialog
          open={!!selectedImei}
          onOpenChange={(nextOpen) => !nextOpen && setSelectedImei(null)}
          imei={selectedImei}
        />
      )}
    </>
  )
}
