import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ChartLine, TrendUp, Package, CurrencyDollar } from '@phosphor-icons/react'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import type { ReportData, Profile } from '@/lib/types'

interface ReportsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  reportData: ReportData
  profile: Profile
}

export function ReportsDialog({ open, onOpenChange, reportData, profile }: ReportsDialogProps) {
  const currency = profile.settings?.currency || 'USD'
  const currencySymbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : '$'

  const formatCurrency = (value: number) => {
    return `${currencySymbol}${value.toLocaleString('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`
  }

  const COLORS = [
    '#4f46e5',
    '#06b6d4',
    '#10b981',
    '#f59e0b',
    '#ef4444',
    '#8b5cf6',
    '#ec4899',
    '#14b8a6',
    '#f97316',
    '#6366f1'
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ChartLine size={24} />
            Reportes y Análisis
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="overview" className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">Resumen</TabsTrigger>
            <TabsTrigger value="trends">Tendencias</TabsTrigger>
            <TabsTrigger value="products">Productos</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <CurrencyDollar size={24} className="text-primary" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Ingresos Totales</p>
                    <p className="text-2xl font-bold">{formatCurrency(reportData.totalRevenue)}</p>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-accent/10 rounded-lg">
                    <Package size={24} className="text-accent" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Órdenes Completadas</p>
                    <p className="text-2xl font-bold">{reportData.totalOrders}</p>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-green-500/10 rounded-lg">
                    <TrendUp size={24} className="text-green-500" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Margen de Ganancia</p>
                    <p className="text-2xl font-bold">{reportData.profitMargin.toFixed(1)}%</p>
                  </div>
                </div>
              </Card>
            </div>

            <Card className="p-6">
              <h3 className="font-semibold mb-4">Promedio de Orden</h3>
              <div className="text-3xl font-bold text-primary">
                {formatCurrency(reportData.totalOrders > 0 ? reportData.totalRevenue / reportData.totalOrders : 0)}
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Por orden completada
              </p>
            </Card>
          </TabsContent>

          <TabsContent value="trends" className="space-y-4">
            <Card className="p-6">
              <h3 className="font-semibold mb-4">Ingresos Mensuales</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={reportData.monthlyTrends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="revenue"
                    stroke="#4f46e5"
                    strokeWidth={2}
                    dot={{ fill: '#4f46e5', r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>

            <Card className="p-6">
              <h3 className="font-semibold mb-4">Órdenes Mensuales</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={reportData.monthlyTrends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="orders" fill="#06b6d4" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </TabsContent>

          <TabsContent value="products" className="space-y-4">
            <Card className="p-6">
              <h3 className="font-semibold mb-4">Top 10 Productos por Ingresos</h3>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={reportData.topProducts} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis
                    type="category"
                    dataKey="product.nombre"
                    width={150}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="revenue" radius={[0, 8, 8, 0]}>
                    {reportData.topProducts.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <div className="space-y-3">
              <h3 className="font-semibold">Detalles de Productos</h3>
              {reportData.topProducts.map((item, index) => (
                <Card key={item.product.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      >
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium">{item.product.nombre}</p>
                        <p className="text-sm text-muted-foreground">
                          {item.product.marca} {item.product.modelo}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-lg">{formatCurrency(item.revenue)}</p>
                      <div className="flex gap-2 mt-1">
                        <Badge variant="outline">{item.quantity} unidades</Badge>
                        <Badge variant="secondary">
                          {formatCurrency(item.revenue / item.quantity)}/u
                        </Badge>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
