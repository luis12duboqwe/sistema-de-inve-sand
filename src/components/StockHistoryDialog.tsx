import { toast } from 'sonner'

import { useState, useEffect, useCallback } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Card } from '@/components/ui/card'
import { ArrowUp, ArrowDown, Download, Calendar } from '@phosphor-icons/react'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { ProductWithStock, StockHistory } from '@/lib/types'

interface StockHistoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock
}

const TIPO_CAMBIO_LABELS: Record<string, string> = {
  'venta': 'Venta',
  'venta_reserva': 'Reserva de Venta',
  'venta_reserva_liberada': 'Reserva Liberada',
  'VENTA_VALIDADA': 'Venta Validada',
  'compra': 'Compra',
  'COMPRA_RECIBIDA': 'Compra Recibida',
  'inicial': 'Inventario Inicial',
  'transferencia_salida': 'Transfer. Salida',
  'transferencia_entrada': 'Transfer. Entrada',
  'transferencia_reserva': 'Transfer. Reservada',
  'transferencia_rechazada': 'Transfer. Rechazada',
  'transferencia_recepcion_parcial': 'Recepción Parcial',
  'ajuste': 'Ajuste Manual',
  'CONTEO_FISICO': 'Conteo Físico',
  'devolucion': 'Devolución'
}

const TIPO_CAMBIO_COLORS: Record<string, string> = {
  'venta': 'bg-blue-500',
  'venta_reserva': 'bg-amber-500',
  'venta_reserva_liberada': 'bg-amber-700',
  'VENTA_VALIDADA': 'bg-blue-600',
  'compra': 'bg-emerald-600',
  'COMPRA_RECIBIDA': 'bg-emerald-700',
  'inicial': 'bg-gray-500',
  'transferencia_salida': 'bg-orange-500',
  'transferencia_entrada': 'bg-green-500',
  'transferencia_reserva': 'bg-yellow-600',
  'transferencia_rechazada': 'bg-red-500',
  'transferencia_recepcion_parcial': 'bg-orange-700',
  'ajuste': 'bg-purple-500',
  'CONTEO_FISICO': 'bg-indigo-500',
  'devolucion': 'bg-cyan-500'
}

export function StockHistoryDialog({ open, onOpenChange, product }: StockHistoryDialogProps) {
  const [history, setHistory] = useState<StockHistory[]>([])
  const [loading, setLoading] = useState(false)
  const [tipoFilter, setTipoFilter] = useState<string>('all')
  const [locationFilter, setLocationFilter] = useState<string>('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [_days, _setDays] = useState(30)

  const loadHistory = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = { limit: 100 }
      if (tipoFilter !== 'all') params.tipo_cambio = tipoFilter
      if (locationFilter !== 'all') params.location_id = Number(locationFilter)
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo

      const data = await inventoryServiceInstance.getStockHistory(product.id, params)
      setHistory(data)
    } catch (error) {
      console.error('Error loading stock history:', error)
      toast.error('Error al cargar historial de stock')
    } finally {
      setLoading(false)
    }
  }, [product.id, tipoFilter, locationFilter, dateFrom, dateTo])

  useEffect(() => {
    if (open) {
      loadHistory()
    }
  }, [open, loadHistory])

  // El filtrado ya se realiza en el backend via loadHistory
  const filteredHistory = history

  const stats = {
    totalMovements: filteredHistory.length,
    totalEntrada: filteredHistory.reduce((sum, h) => sum + (h.cantidad > 0 ? h.cantidad : 0), 0),
    totalSalida: filteredHistory.reduce((sum, h) => sum + (h.cantidad < 0 ? Math.abs(h.cantidad) : 0), 0),
    byType: filteredHistory.reduce((acc, h) => {
      acc[h.tipo_cambio] = (acc[h.tipo_cambio] || 0) + 1
      return acc
    }, {} as Record<string, number>)
  }

  const locationOptions = product.stock_items?.filter(stock => stock.location) ?? []
  const locationName = (locationId?: number) => locationOptions.find(stock => stock.location_id === locationId)?.location?.nombre || (locationId ? `Ubicación #${locationId}` : '')

  const handleExport = () => {
    const csv = [
      ['Fecha', 'Ubicación', 'Tipo', 'Cantidad', 'Stock Anterior', 'Stock Nuevo', 'Referencia', 'Usuario', 'Notas'].join(','),
      ...filteredHistory.map(h => [
        format(new Date(h.created_at), 'dd/MM/yyyy HH:mm'),
        locationName(h.location_id) || '',
        TIPO_CAMBIO_LABELS[h.tipo_cambio] || h.tipo_cambio,
        h.cantidad,
        h.stock_anterior,
        h.stock_nuevo,
        h.referencia_tipo ? `${h.referencia_tipo} #${h.referencia_id}` : '',
        h.usuario || '',
        `"${h.notas || ''}"`
      ].join(','))
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `historial-stock-${product.sku}-${format(new Date(), 'yyyy-MM-dd')}.csv`
    link.click()
    toast.success('Historial exportado')
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar size={24} />
            Historial de Stock - {product.nombre}
          </DialogTitle>
          <DialogDescription>
            Registro completo de todos los movimientos de inventario para este producto
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Estadísticas */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="p-4">
              <div className="text-sm text-muted-foreground mb-1">Total Movimientos</div>
              <div className="text-2xl font-bold">{stats.totalMovements}</div>
            </Card>
            <Card className="p-4">
              <div className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
                <ArrowUp size={16} className="text-green-500" />
                Entradas
              </div>
              <div className="text-2xl font-bold text-green-600">{stats.totalEntrada}</div>
            </Card>
            <Card className="p-4">
              <div className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
                <ArrowDown size={16} className="text-red-500" />
                Salidas
              </div>
              <div className="text-2xl font-bold text-red-600">{stats.totalSalida}</div>
            </Card>
            <Card className="p-4">
              <div className="text-sm text-muted-foreground mb-1">Stock Actual</div>
              <div className="text-2xl font-bold text-primary">{product.stock_disponible}</div>
            </Card>
          </div>

          {/* Filtros */}
          <div className="flex flex-wrap gap-3">
            <div className="flex-1 min-w-[180px]">
              <Label>Tipo de Movimiento</Label>
              <Select value={tipoFilter} onValueChange={setTipoFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="venta">Venta</SelectItem>
                  <SelectItem value="venta_reserva">Reserva de Venta</SelectItem>
                  <SelectItem value="venta_reserva_liberada">Reserva Liberada</SelectItem>
                  <SelectItem value="VENTA_VALIDADA">Venta Validada</SelectItem>
                  <SelectItem value="COMPRA_RECIBIDA">Compra Recibida</SelectItem>
                  <SelectItem value="CONTEO_FISICO">Conteo Físico</SelectItem>
                  <SelectItem value="transferencia_salida">Transfer. Salida</SelectItem>
                  <SelectItem value="transferencia_entrada">Transfer. Entrada</SelectItem>
                  <SelectItem value="transferencia_reserva">Transfer. Reservada</SelectItem>
                  <SelectItem value="transferencia_rechazada">Transfer. Rechazada</SelectItem>
                  <SelectItem value="transferencia_recepcion_parcial">Recepción Parcial</SelectItem>
                  <SelectItem value="ajuste">Ajuste Manual</SelectItem>
                  <SelectItem value="devolucion">Devolución</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {locationOptions.length > 0 && (
              <div className="flex-1 min-w-[180px]">
                <Label>Ubicación</Label>
                <Select value={locationFilter} onValueChange={setLocationFilter}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas</SelectItem>
                    {locationOptions.map(stock => (
                      <SelectItem key={stock.location_id} value={String(stock.location_id)}>
                        {stock.location?.nombre || `Ubicación #${stock.location_id}`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="flex-1 min-w-[140px]">
              <Label>Desde</Label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>

            <div className="flex-1 min-w-[140px]">
              <Label>Hasta</Label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>

            <div className="flex items-end gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setTipoFilter('all')
                  setLocationFilter('all')
                  setDateFrom('')
                  setDateTo('')
                }}
              >
                Limpiar Filtros
              </Button>
              <Button variant="outline" onClick={handleExport}>
                <Download size={18} className="mr-2" />
                Exportar CSV
              </Button>
            </div>
          </div>

          {/* Tabla de Historial */}
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Ubicación</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead className="text-right">Stock Ant.</TableHead>
                  <TableHead className="text-right">Stock Nuevo</TableHead>
                  <TableHead>Referencia</TableHead>
                  <TableHead>Usuario</TableHead>
                  <TableHead>Notas</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      Cargando historial...
                    </TableCell>
                  </TableRow>
                ) : filteredHistory.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      No hay movimientos registrados
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredHistory.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="whitespace-nowrap">
                        {format(new Date(item.created_at), 'dd/MM/yyyy HH:mm', { locale: es })}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {locationName(item.location_id) || '-'}
                      </TableCell>
                      <TableCell>
                        <Badge className={TIPO_CAMBIO_COLORS[item.tipo_cambio]}>
                          {TIPO_CAMBIO_LABELS[item.tipo_cambio] || item.tipo_cambio}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={item.cantidad > 0 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                          {item.cantidad > 0 ? '+' : ''}{item.cantidad}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">{item.stock_anterior}</TableCell>
                      <TableCell className="text-right font-semibold">{item.stock_nuevo}</TableCell>
                      <TableCell>
                        {item.referencia_tipo && (
                          <span className="text-sm text-muted-foreground">
                            {item.referencia_tipo} #{item.referencia_id}
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">{item.usuario || '-'}</TableCell>
                      <TableCell className="text-sm max-w-[200px] truncate" title={item.notas || ''}>
                        {item.notas || '-'}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Resumen por Tipo */}
          {Object.keys(stats.byType).length > 0 && (
            <Card className="p-4">
              <h3 className="font-semibold mb-3">Movimientos por Tipo</h3>
              <div className="flex flex-wrap gap-4">
                {Object.entries(stats.byType).map(([tipo, count]) => (
                  <div key={tipo} className="flex items-center gap-2">
                    <Badge className={TIPO_CAMBIO_COLORS[tipo]}>
                      {TIPO_CAMBIO_LABELS[tipo] || tipo}
                    </Badge>
                    <span className="font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
