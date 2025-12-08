import { useState, useEffect, useCallback } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
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
import type { StockHistory, ProductWithStock } from '@/lib/types'
import { toast } from 'sonner'

interface StockHistoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock
}

const TIPO_CAMBIO_LABELS: Record<string, string> = {
  'venta': 'Venta',
  'transferencia_salida': 'Transfer. Salida',
  'transferencia_entrada': 'Transfer. Entrada',
  'ajuste': 'Ajuste Manual',
  'devolucion': 'Devolución'
}

const TIPO_CAMBIO_COLORS: Record<string, string> = {
  'venta': 'bg-blue-500',
  'transferencia_salida': 'bg-orange-500',
  'transferencia_entrada': 'bg-green-500',
  'ajuste': 'bg-purple-500',
  'devolucion': 'bg-cyan-500'
}

export function StockHistoryDialog({ open, onOpenChange, product }: StockHistoryDialogProps) {
  const [history, setHistory] = useState<StockHistory[]>([])
  const [loading, setLoading] = useState(false)
  const [tipoFilter, setTipoFilter] = useState<string>('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [_days, _setDays] = useState(30)

  const loadHistory = useCallback(async () => {
    setLoading(true)
    try {
      // Por ahora simulamos datos porque el endpoint necesita estar configurado
      // En producción, esto llamaría a: GET /api/stock-history/product/{product.id}
      
      // Simular datos de ejemplo
      const mockHistory: StockHistory[] = [
        {
          id: 1,
          product_id: product.id,
          tipo_cambio: 'ajuste',
          cantidad: product.stock_disponible,
          stock_anterior: 0,
          stock_nuevo: product.stock_disponible,
          notas: 'Stock inicial',
          usuario: 'Sistema',
          created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
        }
      ]
      
      setHistory(mockHistory)
      
      // TODO: Implementar llamada real a API cuando esté disponible
      // const params = new URLSearchParams()
      // if (tipoFilter !== 'all') params.append('tipo_cambio', tipoFilter)
      // if (dateFrom) params.append('date_from', dateFrom)
      // if (dateTo) params.append('date_to', dateTo)
      // params.append('limit', '100')
      // 
      // const response = await fetch(`/api/stock-history/product/${product.id}?${params}`)
      // const data = await response.json()
      // setHistory(data)
      
    } catch (error) {
      console.error('Error loading stock history:', error)
      toast.error('Error al cargar historial de stock')
    } finally {
      setLoading(false)
    }
  }, [product.id, product.stock_disponible])

  useEffect(() => {
    if (open) {
      loadHistory()
    }
  }, [open, loadHistory])

  const filteredHistory = history.filter(h => {
    if (tipoFilter !== 'all' && h.tipo_cambio !== tipoFilter) return false
    
    if (dateFrom) {
      const hDate = new Date(h.created_at)
      const fromDate = new Date(dateFrom)
      if (hDate < fromDate) return false
    }
    
    if (dateTo) {
      const hDate = new Date(h.created_at)
      const toDate = new Date(dateTo)
      toDate.setHours(23, 59, 59, 999)
      if (hDate > toDate) return false
    }
    
    return true
  })

  const stats = {
    totalMovements: filteredHistory.length,
    totalEntrada: filteredHistory.reduce((sum, h) => sum + (h.cantidad > 0 ? h.cantidad : 0), 0),
    totalSalida: filteredHistory.reduce((sum, h) => sum + (h.cantidad < 0 ? Math.abs(h.cantidad) : 0), 0),
    byType: filteredHistory.reduce((acc, h) => {
      acc[h.tipo_cambio] = (acc[h.tipo_cambio] || 0) + 1
      return acc
    }, {} as Record<string, number>)
  }

  const handleExport = () => {
    const csv = [
      ['Fecha', 'Tipo', 'Cantidad', 'Stock Anterior', 'Stock Nuevo', 'Referencia', 'Usuario', 'Notas'].join(','),
      ...filteredHistory.map(h => [
        format(new Date(h.created_at), 'dd/MM/yyyy HH:mm'),
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
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar size={24} />
            Historial de Stock - {product.nombre}
          </DialogTitle>
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
                  <SelectItem value="transferencia_salida">Transfer. Salida</SelectItem>
                  <SelectItem value="transferencia_entrada">Transfer. Entrada</SelectItem>
                  <SelectItem value="ajuste">Ajuste Manual</SelectItem>
                  <SelectItem value="devolucion">Devolución</SelectItem>
                </SelectContent>
              </Select>
            </div>

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
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      Cargando historial...
                    </TableCell>
                  </TableRow>
                ) : filteredHistory.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      No hay movimientos registrados
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredHistory.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="whitespace-nowrap">
                        {format(new Date(item.created_at), 'dd/MM/yyyy HH:mm', { locale: es })}
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
