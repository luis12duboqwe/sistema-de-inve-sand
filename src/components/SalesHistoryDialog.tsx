import { useMemo, useState } from 'react'
import { format } from 'date-fns'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { Location, OrderWithItems, SalesProfile } from '@/lib/types'

interface SalesHistoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  orders: OrderWithItems[]
  locations: Location[]
  salesProfiles: SalesProfile[]
}

type EnrichedOrder = OrderWithItems & {
  sellerName: string
  locationName: string
}

function getChannelLabel(channel?: string): string {
  if (!channel) return 'N/A'
  const map: Record<string, string> = {
    whatsapp: 'WhatsApp',
    facebook: 'Facebook',
    instagram: 'Instagram',
    tienda: 'Tienda Física'
  }
  return map[channel] || channel
}

function getWeekKey(date: Date): string {
  const weekday = date.getDay() === 0 ? 7 : date.getDay()
  const monday = new Date(date)
  monday.setDate(date.getDate() - (weekday - 1))
  monday.setHours(0, 0, 0, 0)
  return format(monday, 'yyyy-MM-dd')
}

function downloadCsv(filename: string, rows: string[][]) {
  const escapeCsv = (value: string | number) => {
    const raw = String(value ?? '')
    if (raw.includes(',') || raw.includes('"') || raw.includes('\n')) {
      return `"${raw.replace(/"/g, '""')}"`
    }
    return raw
  }

  const csv = rows.map(row => row.map(escapeCsv).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function SalesHistoryDialog({
  open,
  onOpenChange,
  orders,
  locations,
  salesProfiles,
}: SalesHistoryDialogProps) {
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [locationFilter, setLocationFilter] = useState('all')
  const [profileFilter, setProfileFilter] = useState('all')
  const [channelFilter, setChannelFilter] = useState('all')

  const completedOrders = useMemo<EnrichedOrder[]>(() => {
    const locationMap = new Map(locations.map(location => [location.id, location.nombre]))
    const profileMap = new Map(salesProfiles.map(profile => [profile.id, profile.name]))

    return orders
      .filter(order => order.estado === 'completada')
      .map(order => ({
        ...order,
        sellerName: order.sales_profile_id
          ? (profileMap.get(order.sales_profile_id) || `Perfil #${order.sales_profile_id}`)
          : 'Sin perfil',
        locationName: order.source_location_id
          ? (locationMap.get(order.source_location_id) || `Ubicación #${order.source_location_id}`)
          : 'Sin ubicación',
      }))
  }, [orders, locations, salesProfiles])

  const filteredOrders = useMemo(() => {
    return completedOrders
      .filter(order => {
        if (locationFilter !== 'all' && String(order.source_location_id) !== locationFilter) return false
        if (profileFilter !== 'all' && String(order.sales_profile_id) !== profileFilter) return false
        if (channelFilter !== 'all' && order.canal !== channelFilter) return false

        if (dateFrom) {
          const from = new Date(dateFrom)
          from.setHours(0, 0, 0, 0)
          if (new Date(order.created_at) < from) return false
        }

        if (dateTo) {
          const to = new Date(dateTo)
          to.setHours(23, 59, 59, 999)
          if (new Date(order.created_at) > to) return false
        }

        return true
      })
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  }, [completedOrders, locationFilter, profileFilter, channelFilter, dateFrom, dateTo])

  const dailySummary = useMemo(() => {
    const map = new Map<string, { date: string; orders: number; total: number }>()

    for (const order of filteredOrders) {
      const dateKey = format(new Date(order.created_at), 'yyyy-MM-dd')
      const current = map.get(dateKey) || { date: dateKey, orders: 0, total: 0 }
      current.orders += 1
      current.total += Number(order.total || 0)
      map.set(dateKey, current)
    }

    return Array.from(map.values()).sort((a, b) => b.date.localeCompare(a.date))
  }, [filteredOrders])

  const weeklySummary = useMemo(() => {
    const map = new Map<string, { weekStart: string; orders: number; total: number }>()

    for (const order of filteredOrders) {
      const weekKey = getWeekKey(new Date(order.created_at))
      const current = map.get(weekKey) || { weekStart: weekKey, orders: 0, total: 0 }
      current.orders += 1
      current.total += Number(order.total || 0)
      map.set(weekKey, current)
    }

    return Array.from(map.values()).sort((a, b) => b.weekStart.localeCompare(a.weekStart))
  }, [filteredOrders])

  const totalSales = useMemo(
    () => filteredOrders.reduce((sum, order) => sum + Number(order.total || 0), 0),
    [filteredOrders]
  )

  const exportTransactionsCsv = () => {
    const rows: string[][] = [
      ['Orden', 'Fecha', 'Cliente', 'Vendedor', 'Ubicación', 'Canal', 'Método de Pago', 'Total']
    ]

    filteredOrders.forEach(order => {
      rows.push([
        String(order.id),
        format(new Date(order.created_at), 'dd/MM/yyyy HH:mm'),
        order.customer_name || 'N/A',
        order.sellerName,
        order.locationName,
        getChannelLabel(order.canal),
        order.metodo_pago || 'N/A',
        String(Number(order.total || 0))
      ])
    })

    downloadCsv('historial_ventas_transacciones.csv', rows)
  }

  const exportDailyCsv = () => {
    const rows: string[][] = [['Fecha', 'Órdenes', 'Total']]
    dailySummary.forEach(row => {
      rows.push([format(new Date(row.date), 'dd/MM/yyyy'), String(row.orders), String(row.total)])
    })
    downloadCsv('historial_ventas_diario.csv', rows)
  }

  const exportWeeklyCsv = () => {
    const rows: string[][] = [['Semana (inicio)', 'Órdenes', 'Total']]
    weeklySummary.forEach(row => {
      rows.push([format(new Date(row.weekStart), 'dd/MM/yyyy'), String(row.orders), String(row.total)])
    })
    downloadCsv('historial_ventas_semanal.csv', rows)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-7xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Historial de Ventas</DialogTitle>
          <DialogDescription>
            Revisa ventas por transacción, resumen diario y semanal, incluyendo quién vendió y dónde se vendió.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mt-2">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Desde</label>
            <Input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Hasta</label>
            <Input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Ubicación</label>
            <Select value={locationFilter} onValueChange={setLocationFilter}>
              <SelectTrigger><SelectValue placeholder="Todas" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                {locations.map(location => (
                  <SelectItem key={location.id} value={String(location.id)}>{location.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Vendedor/Perfil</label>
            <Select value={profileFilter} onValueChange={setProfileFilter}>
              <SelectTrigger><SelectValue placeholder="Todos" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {salesProfiles.map(profile => (
                  <SelectItem key={profile.id} value={String(profile.id)}>{profile.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Canal</label>
            <Select value={channelFilter} onValueChange={setChannelFilter}>
              <SelectTrigger><SelectValue placeholder="Todos" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="whatsapp">WhatsApp</SelectItem>
                <SelectItem value="facebook">Facebook</SelectItem>
                <SelectItem value="instagram">Instagram</SelectItem>
                <SelectItem value="tienda">Tienda Física</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 items-center mt-3">
          <Badge variant="secondary">Órdenes: {filteredOrders.length}</Badge>
          <Badge variant="secondary">Total: HNL {totalSales.toLocaleString()}</Badge>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setDateFrom('')
              setDateTo('')
              setLocationFilter('all')
              setProfileFilter('all')
              setChannelFilter('all')
            }}
          >
            Limpiar filtros
          </Button>
        </div>

        <Tabs defaultValue="transactions" className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="transactions">Transacciones</TabsTrigger>
            <TabsTrigger value="daily">Resumen Diario</TabsTrigger>
            <TabsTrigger value="weekly">Resumen Semanal</TabsTrigger>
          </TabsList>

          <TabsContent value="transactions" className="space-y-3">
            <div className="flex justify-end">
              <Button type="button" variant="outline" size="sm" onClick={exportTransactionsCsv}>
                Exportar CSV
              </Button>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Orden</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Vendedor</TableHead>
                  <TableHead>Ubicación</TableHead>
                  <TableHead>Canal</TableHead>
                  <TableHead>Método</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredOrders.map(order => (
                  <TableRow key={order.id}>
                    <TableCell>#{order.id}</TableCell>
                    <TableCell>{format(new Date(order.created_at), 'dd/MM/yyyy HH:mm')}</TableCell>
                    <TableCell>{order.customer_name || 'N/A'}</TableCell>
                    <TableCell>{order.sellerName}</TableCell>
                    <TableCell>{order.locationName}</TableCell>
                    <TableCell>{getChannelLabel(order.canal)}</TableCell>
                    <TableCell>{order.metodo_pago || 'N/A'}</TableCell>
                    <TableCell className="text-right">HNL {Number(order.total || 0).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TabsContent>

          <TabsContent value="daily" className="space-y-3">
            <div className="flex justify-end">
              <Button type="button" variant="outline" size="sm" onClick={exportDailyCsv}>
                Exportar CSV Diario
              </Button>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Órdenes</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dailySummary.map(row => (
                  <TableRow key={row.date}>
                    <TableCell>{format(new Date(row.date), 'dd/MM/yyyy')}</TableCell>
                    <TableCell>{row.orders}</TableCell>
                    <TableCell className="text-right">HNL {row.total.toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TabsContent>

          <TabsContent value="weekly" className="space-y-3">
            <div className="flex justify-end">
              <Button type="button" variant="outline" size="sm" onClick={exportWeeklyCsv}>
                Exportar CSV Semanal
              </Button>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Semana (inicio)</TableHead>
                  <TableHead>Órdenes</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {weeklySummary.map(row => (
                  <TableRow key={row.weekStart}>
                    <TableCell>{format(new Date(row.weekStart), 'dd/MM/yyyy')}</TableCell>
                    <TableCell>{row.orders}</TableCell>
                    <TableCell className="text-right">HNL {row.total.toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
