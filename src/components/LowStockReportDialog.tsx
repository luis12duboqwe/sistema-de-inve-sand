import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Warning, Package, Download, TrendDown } from '@phosphor-icons/react'
import type { ProductWithStock, Profile } from '@/lib/types'

interface LowStockReportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  products: ProductWithStock[]
  profiles: Profile[]
  onProductClick?: (product: ProductWithStock) => void
}

export function LowStockReportDialog({
  open,
  onOpenChange,
  products,
  profiles,
  onProductClick
}: LowStockReportDialogProps) {
  // V2.0: Stock alerts should be by LOCATION not profile
  // TODO: Refactor to use locations from API instead of profiles
  // For now, showing all products globally as interim solution
  const [selectedProfile, setSelectedProfile] = useState<string>('all')
  const [severityFilter, setSeverityFilter] = useState<'all' | 'out' | 'critical' | 'low'>('all')

  const activeProfiles = profiles.filter(p => p.active && p.settings?.enableNotifications)

  const getLowStockProducts = () => {
    const lowStockMap: Record<string, {
      profile: Profile
      outOfStock: ProductWithStock[]
      critical: ProductWithStock[]
      low: ProductWithStock[]
    }> = {}

    activeProfiles.forEach(profile => {
      const threshold = profile.settings?.lowStockThreshold || 5
      // V2.0 INTERIM: Products are global - this should check stock by location
      const profileProducts = products.filter(
        p => p.activo
      )

      const lowStockProducts = profileProducts.filter(
        p => p.stock_disponible <= threshold
      )

      if (lowStockProducts.length > 0) {
        lowStockMap[profile.slug] = {
          profile,
          outOfStock: lowStockProducts.filter(p => p.stock_disponible === 0),
          critical: lowStockProducts.filter(
            p => p.stock_disponible > 0 && p.stock_disponible <= Math.floor(threshold / 2)
          ),
          low: lowStockProducts.filter(
            p => p.stock_disponible > Math.floor(threshold / 2)
          )
        }
      }
    })

    return lowStockMap
  }

  const lowStockMap = getLowStockProducts()

  const getFilteredProducts = () => {
    let allProducts: Array<{
      product: ProductWithStock
      profile: Profile
      severity: 'out' | 'critical' | 'low'
    }> = []

    Object.values(lowStockMap).forEach(({ profile, outOfStock, critical, low }) => {
      if (selectedProfile === 'all' || profile.slug === selectedProfile) {
        outOfStock.forEach(p => allProducts.push({ product: p, profile, severity: 'out' }))
        critical.forEach(p => allProducts.push({ product: p, profile, severity: 'critical' }))
        low.forEach(p => allProducts.push({ product: p, profile, severity: 'low' }))
      }
    })

    if (severityFilter !== 'all') {
      allProducts = allProducts.filter(item => item.severity === severityFilter)
    }

    return allProducts
  }

  const filteredProducts = getFilteredProducts()

  const getTotalsByProfile = () => {
    return Object.values(lowStockMap).map(({ profile, outOfStock, critical, low }) => ({
      profile,
      total: outOfStock.length + critical.length + low.length,
      outOfStock: outOfStock.length,
      critical: critical.length,
      low: low.length
    }))
  }

  const exportReport = () => {
    const csvContent = [
      ['Perfil', 'Producto', 'SKU', 'Marca', 'Modelo', 'Stock Actual', 'Umbral', 'Severidad'].join(','),
      ...filteredProducts.map(({ product, profile, severity }) =>
        [
          profile.name,
          product.nombre,
          product.sku,
          product.marca,
          product.modelo,
          product.stock_disponible,
          profile.settings?.lowStockThreshold || 5,
          severity === 'out' ? 'Agotado' : severity === 'critical' ? 'Crítico' : 'Bajo'
        ].join(',')
      )
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `reporte-stock-bajo-${new Date().toISOString().split('T')[0]}.csv`)
    link.click()
  }

  const getSeverityBadge = (severity: 'out' | 'critical' | 'low') => {
    switch (severity) {
      case 'out':
        return <Badge variant="destructive">Agotado</Badge>
      case 'critical':
        return <Badge className="bg-yellow-500 text-white">Crítico</Badge>
      case 'low':
        return <Badge variant="secondary">Bajo</Badge>
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TrendDown size={24} className="text-destructive" weight="duotone" />
            Reporte de Stock Bajo
          </DialogTitle>
          <DialogDescription>
            Visualiza todos los productos con stock bajo o agotado
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="products" className="flex-1">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="products">Productos</TabsTrigger>
            <TabsTrigger value="summary">Resumen por Perfil</TabsTrigger>
          </TabsList>

          <TabsContent value="products" className="space-y-4 mt-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <Select value={selectedProfile} onValueChange={setSelectedProfile}>
                <SelectTrigger className="w-full sm:w-[200px]">
                  <SelectValue placeholder="Perfil" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los perfiles</SelectItem>
                  {activeProfiles.map(profile => (
                    <SelectItem key={profile.id} value={profile.slug}>
                      {profile.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={severityFilter} onValueChange={(v) => setSeverityFilter(v as any)}>
                <SelectTrigger className="w-full sm:w-[200px]">
                  <SelectValue placeholder="Severidad" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  <SelectItem value="out">Agotado</SelectItem>
                  <SelectItem value="critical">Crítico</SelectItem>
                  <SelectItem value="low">Bajo</SelectItem>
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                onClick={exportReport}
                className="flex-1 sm:flex-none ml-auto"
              >
                <Download size={16} className="mr-2" />
                Exportar
              </Button>
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">
                {filteredProducts.length} producto{filteredProducts.length !== 1 ? 's' : ''}
              </Badge>
              <Badge variant="destructive">
                {filteredProducts.filter(p => p.severity === 'out').length} agotado{filteredProducts.filter(p => p.severity === 'out').length !== 1 ? 's' : ''}
              </Badge>
              <Badge className="bg-yellow-500 text-white">
                {filteredProducts.filter(p => p.severity === 'critical').length} crítico{filteredProducts.filter(p => p.severity === 'critical').length !== 1 ? 's' : ''}
              </Badge>
            </div>

            <ScrollArea className="h-[400px] pr-4">
              {filteredProducts.length === 0 ? (
                <div className="text-center py-12">
                  <Package size={48} className="mx-auto text-muted-foreground mb-3" weight="duotone" />
                  <p className="text-sm text-muted-foreground">
                    No hay productos con stock bajo
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredProducts.map(({ product, profile, severity }) => (
                    <Card
                      key={product.id}
                      className="p-4 cursor-pointer hover:bg-accent/20 transition-colors"
                      onClick={() => onProductClick?.(product)}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          <Warning
                            size={20}
                            weight="fill"
                            className={
                              severity === 'out'
                                ? 'text-destructive'
                                : severity === 'critical'
                                ? 'text-yellow-500'
                                : 'text-muted-foreground'
                            }
                          />
                          <div className="flex-1 min-w-0 space-y-1">
                            <div className="flex items-start gap-2 flex-wrap">
                              <p className="text-sm font-medium">{product.nombre}</p>
                              {getSeverityBadge(severity)}
                            </div>
                            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                              <span>{product.marca} {product.modelo}</span>
                              <span>•</span>
                              <span>SKU: {product.sku}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-xs">
                                {profile.name}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                Stock: {product.stock_disponible} / Umbral: {profile.settings?.lowStockThreshold || 5}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="summary" className="space-y-4 mt-4">
            <ScrollArea className="h-[500px] pr-4">
              {getTotalsByProfile().length === 0 ? (
                <div className="text-center py-12">
                  <Package size={48} className="mx-auto text-muted-foreground mb-3" weight="duotone" />
                  <p className="text-sm text-muted-foreground">
                    No hay alertas de stock
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {getTotalsByProfile().map(({ profile, total, outOfStock, critical, low }) => (
                    <Card key={profile.id} className="p-4">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <h3 className="text-lg font-semibold">{profile.name}</h3>
                          <Badge variant="outline">
                            {total} producto{total !== 1 ? 's' : ''}
                          </Badge>
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                          <div className="text-center p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                            <p className="text-2xl font-bold text-destructive">{outOfStock}</p>
                            <p className="text-xs text-muted-foreground">Agotado{outOfStock !== 1 ? 's' : ''}</p>
                          </div>

                          <div className="text-center p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                            <p className="text-2xl font-bold text-yellow-600">{critical}</p>
                            <p className="text-xs text-muted-foreground">Crítico{critical !== 1 ? 's' : ''}</p>
                          </div>

                          <div className="text-center p-3 rounded-lg bg-secondary border">
                            <p className="text-2xl font-bold text-secondary-foreground">{low}</p>
                            <p className="text-xs text-muted-foreground">Bajo{low !== 1 ? 's' : ''}</p>
                          </div>
                        </div>

                        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
                          <span>Umbral configurado: {profile.settings?.lowStockThreshold || 5} unidades</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedProfile(profile.slug)}
                            className="h-7"
                          >
                            Ver detalles
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
