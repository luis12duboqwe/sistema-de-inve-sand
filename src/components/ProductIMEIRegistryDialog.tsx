import { useEffect, useMemo, useState } from 'react'
import { format } from 'date-fns'
import { Barcode, ClockCounterClockwise, PencilSimple, Plus } from '@phosphor-icons/react'
import { toast } from 'sonner'

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
import { apiClient } from '@/lib/apiClient'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { Location, ProductIMEI, ProductWithStock } from '@/lib/types'

import { IMEIHistoryDialog } from './IMEIHistoryDialog'
import { PrintButton } from './ProductLabel'

interface ProductIMEIRegistryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock
  allowAdminActions?: boolean
  locations?: Location[]
  onUpdated?: () => Promise<void> | void
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

export function ProductIMEIRegistryDialog({ open, onOpenChange, product, allowAdminActions = false, locations = [], onUpdated }: ProductIMEIRegistryDialogProps) {
  const [imeiRecords, setImeiRecords] = useState<ProductIMEI[]>([])
  const [loading, setLoading] = useState(false)
  const [savingAdminAction, setSavingAdminAction] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedImei, setSelectedImei] = useState<string | null>(null)
  const [isSuperAdmin, setIsSuperAdmin] = useState(false)
  const [adminImei, setAdminImei] = useState('')
  const [adminReason, setAdminReason] = useState('')
  const [adminLocationId, setAdminLocationId] = useState<string>('')
  const [editingRecord, setEditingRecord] = useState<ProductIMEI | null>(null)
  const [editedImei, setEditedImei] = useState('')
  const [editReason, setEditReason] = useState('')
  const isSerializedProduct = Boolean(product.is_serialized || product.categoria === 'celular')
  const canUseAdminActions = allowAdminActions || isSuperAdmin

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

  useEffect(() => {
    const loadCurrentUser = async () => {
      try {
        const user = await apiClient.getCurrentUser()
        setIsSuperAdmin(!!user.is_superuser)
      } catch {
        setIsSuperAdmin(false)
      }
    }

    if (open) {
      void loadCurrentUser()
      const firstStockLocation = product.stock_items?.find(item => item.location_id)?.location_id
      setAdminLocationId(firstStockLocation ? String(firstStockLocation) : '')
      setAdminImei('')
      setAdminReason('')
      setEditingRecord(null)
      setEditedImei('')
      setEditReason('')
    }
  }, [open, product.stock_items])

  const reloadImeiRecords = async () => {
    const records = await inventoryServiceInstance.getProductIMEIs(product.id)
    setImeiRecords(records)
  }

  const handleAddMissingImei = async () => {
    const imei = adminImei.trim()
    const reason = adminReason.trim()
    const locationId = Number(adminLocationId)
    if (!/^\d{15}$/.test(imei)) {
      toast.error('El IMEI debe tener exactamente 15 dígitos')
      return
    }
    if (!locationId) {
      toast.error('Selecciona la ubicación donde está el equipo')
      return
    }
    if (reason.length < 5) {
      toast.error('Escribe el motivo de la corrección')
      return
    }

    setSavingAdminAction(true)
    try {
      await inventoryServiceInstance.adminAddMissingIMEI({
        product_id: product.id,
        location_id: locationId,
        imei,
        reason,
      })
      await reloadImeiRecords()
      await onUpdated?.()
      setAdminImei('')
      setAdminReason('')
      toast.success('IMEI agregado con historial administrativo')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo agregar el IMEI')
    } finally {
      setSavingAdminAction(false)
    }
  }

  const startEditRecord = (record: ProductIMEI) => {
    setEditingRecord(record)
    setEditedImei(record.imei)
    setEditReason('')
  }

  const handleCorrectImei = async () => {
    if (!editingRecord) return
    const newImei = editedImei.trim()
    const reason = editReason.trim()
    if (!/^\d{15}$/.test(newImei)) {
      toast.error('El IMEI debe tener exactamente 15 dígitos')
      return
    }
    if (newImei === editingRecord.imei) {
      toast.error('El nuevo IMEI es igual al actual')
      return
    }
    if (reason.length < 5) {
      toast.error('Escribe el motivo de la corrección')
      return
    }

    setSavingAdminAction(true)
    try {
      await inventoryServiceInstance.adminCorrectIMEI(editingRecord.id, { new_imei: newImei, reason })
      await reloadImeiRecords()
      await onUpdated?.()
      setEditingRecord(null)
      setEditedImei('')
      setEditReason('')
      toast.success('IMEI corregido con historial administrativo')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo corregir el IMEI')
    } finally {
      setSavingAdminAction(false)
    }
  }

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

  const stockLocationOptions = useMemo(() => {
    if (canUseAdminActions && locations.length > 0) {
      return locations
        .filter(location => location.activo !== false)
        .map(location => {
          const stock = product.stock_items?.find(item => item.location_id === location.id)
          return {
            id: location.id,
            name: location.nombre,
            stock: stock?.cantidad_disponible ?? 0,
          }
        })
    }

    return (product.stock_items || [])
      .filter(item => item.location_id)
      .map(item => ({
        id: item.location_id,
        name: item.location?.nombre || `Ubicación ${item.location_id}`,
        stock: item.cantidad_disponible,
      }))
  }, [canUseAdminActions, locations, product.stock_items])

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

            {canUseAdminActions && isSerializedProduct && (
              <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-amber-950">Corrección administrativa de IMEI</div>
                    <div className="text-xs text-amber-900">Solo para corregir inventario inconsistente o errores de digitación.</div>
                  </div>
                  <Badge variant="outline" className="border-amber-500 text-amber-900">Super admin</Badge>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-[160px_180px_1fr_auto] gap-2">
                  <Input
                    value={adminImei}
                    onChange={(event) => setAdminImei(event.target.value.replace(/\D/g, '').slice(0, 15))}
                    placeholder="IMEI faltante"
                    inputMode="numeric"
                  />
                  <select
                    className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                    value={adminLocationId}
                    onChange={(event) => setAdminLocationId(event.target.value)}
                  >
                    <option value="">Ubicación</option>
                    {stockLocationOptions.map(option => (
                      <option key={option.id} value={option.id}>{option.name} ({option.stock})</option>
                    ))}
                  </select>
                  <Input
                    value={adminReason}
                    onChange={(event) => setAdminReason(event.target.value)}
                    placeholder="Motivo obligatorio"
                  />
                  <Button onClick={handleAddMissingImei} disabled={savingAdminAction || stockLocationOptions.length === 0}>
                    <Plus size={16} /> Agregar
                  </Button>
                </div>

                {editingRecord && (
                  <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr_auto_auto] gap-2 border-t border-amber-200 pt-3">
                    <Input
                      value={editedImei}
                      onChange={(event) => setEditedImei(event.target.value.replace(/\D/g, '').slice(0, 15))}
                      placeholder="Nuevo IMEI"
                      inputMode="numeric"
                    />
                    <Input
                      value={editReason}
                      onChange={(event) => setEditReason(event.target.value)}
                      placeholder="Motivo obligatorio"
                    />
                    <Button onClick={handleCorrectImei} disabled={savingAdminAction}>Guardar</Button>
                    <Button variant="outline" onClick={() => setEditingRecord(null)} disabled={savingAdminAction}>Cancelar</Button>
                  </div>
                )}
              </div>
            )}

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
                            {canUseAdminActions && !record.vendido && !record.order_id && !record.transfer_id && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => startEditRecord(record)}
                                title="Corregir IMEI"
                              >
                                <PencilSimple size={16} />
                              </Button>
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
