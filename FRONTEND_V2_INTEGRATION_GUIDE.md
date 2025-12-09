# 🎨 Guía de Integración Frontend V2.0

## ✅ Completado

### 1. Tipos TypeScript (`src/lib/types.ts`)
- ✅ `Location` - Ubicaciones físicas
- ✅ `SalesProfile` - Perfiles de venta
- ✅ `StockByLocation` - Stock por ubicación
- ✅ `Product` - Actualizado con `stock_items?: StockByLocation[]`
- ✅ `Order` - Actualizado con `sales_profile_id` y `source_location_id`
- ✅ `CreateOrderRequest` - Actualizado con campos V2.0

### 2. Componentes UI
- ✅ `LocationsList` - CRUD completo de ubicaciones
- ✅ `SalesProfilesList` - CRUD completo de perfiles de venta
- ✅ App.tsx - Nuevas pestañas "Ubicaciones" y "Perfiles Venta"

---

## ⏳ Pendiente de Implementación

### 3. Actualizar `NewProductDialog.tsx`

**Objetivo:** Permitir asignar stock a ubicaciones específicas al crear un producto.

**Cambios necesarios:**

```typescript
// 1. Importar Location
import type { Location } from '@/lib/types'

// 2. Cargar ubicaciones disponibles
const [locations, setLocations] = useState<Location[]>([])
const [stockByLocation, setStockByLocation] = useState<Record<number, number>>({})

useEffect(() => {
  const loadLocations = async () => {
    try {
      const response = await fetch(`${API_URL}/locations?activo=true`)
      const data = await response.json()
      setLocations(data)
    } catch (error) {
      console.error('Error al cargar ubicaciones:', error)
    }
  }
  if (open) loadLocations()
}, [open])

// 3. Agregar sección de stock por ubicación en el formulario
<div className="space-y-2">
  <Label>Stock por Ubicación</Label>
  {locations.map((location) => (
    <div key={location.id} className="flex items-center justify-between border p-3 rounded-md">
      <div>
        <p className="font-medium">{location.nombre}</p>
        <p className="text-sm text-gray-500">{location.tipo}</p>
      </div>
      <Input
        type="number"
        min="0"
        value={stockByLocation[location.id] || 0}
        onChange={(e) => setStockByLocation({
          ...stockByLocation,
          [location.id]: parseInt(e.target.value) || 0
        })}
        className="w-24"
        placeholder="0"
      />
    </div>
  ))}
</div>

// 4. Al crear el producto, también crear el stock por ubicación
const handleSubmit = async () => {
  // ... crear producto primero ...
  
  // Luego asignar stock a cada ubicación
  for (const [locationId, cantidad] of Object.entries(stockByLocation)) {
    if (cantidad > 0) {
      await fetch(`${API_URL}/products/${productId}/stock/location/${locationId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cantidad })
      })
    }
  }
}
```

---

### 4. Actualizar `EditProductDialog.tsx`

**Objetivo:** Mostrar y editar stock por ubicación de productos existentes.

**Cambios necesarios:**

```typescript
// 1. Cargar stock por ubicación del producto
const [stockByLocation, setStockByLocation] = useState<StockByLocation[]>([])

useEffect(() => {
  const loadStockByLocation = async () => {
    if (!product) return
    try {
      const response = await fetch(`${API_URL}/products/${product.id}/stock/by-location`)
      const data = await response.json()
      setStockByLocation(data.items || [])
    } catch (error) {
      console.error('Error al cargar stock:', error)
    }
  }
  if (open && product) loadStockByLocation()
}, [open, product])

// 2. Mostrar stock actual por ubicación con opción de editar
<div className="space-y-2">
  <Label>Stock por Ubicación</Label>
  <div className="border rounded-md p-3 space-y-2">
    <div className="flex justify-between items-center font-semibold">
      <span>Total:</span>
      <span>{stockByLocation.reduce((sum, s) => sum + s.cantidad_disponible, 0)}</span>
    </div>
    {stockByLocation.map((stock) => (
      <div key={stock.location_id} className="flex justify-between items-center">
        <span>{stock.location?.nombre || `Ubicación ${stock.location_id}`}</span>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            min="0"
            value={stock.cantidad_disponible}
            onChange={(e) => handleUpdateStock(stock.location_id, parseInt(e.target.value))}
            className="w-20"
          />
          <Button
            size="sm"
            onClick={() => saveStockForLocation(stock.location_id, stock.cantidad_disponible)}
          >
            Guardar
          </Button>
        </div>
      </div>
    ))}
  </div>
</div>

const handleUpdateStock = (locationId: number, cantidad: number) => {
  setStockByLocation((prev) =>
    prev.map((s) => (s.location_id === locationId ? { ...s, cantidad_disponible: cantidad } : s))
  )
}

const saveStockForLocation = async (locationId: number, cantidad: number) => {
  try {
    await fetch(`${API_URL}/products/${product.id}/stock/location/${locationId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cantidad })
    })
    toast.success('Stock actualizado')
  } catch (error) {
    toast.error('Error al actualizar stock')
  }
}
```

---

### 5. Actualizar `NewOrderDialog.tsx`

**Objetivo:** Seleccionar perfil de venta y ubicación origen al crear órdenes.

**Cambios necesarios:**

```typescript
// 1. Importar tipos y cargar datos
import type { SalesProfile, Location } from '@/lib/types'

const [salesProfiles, setSalesProfiles] = useState<SalesProfile[]>([])
const [locations, setLocations] = useState<Location[]>([])
const [selectedSalesProfile, setSelectedSalesProfile] = useState<string>('')
const [selectedLocation, setSelectedLocation] = useState<number | null>(null)

useEffect(() => {
  const loadData = async () => {
    try {
      const [profilesRes, locationsRes] = await Promise.all([
        fetch(`${API_URL}/sales-profiles?activo=true`),
        fetch(`${API_URL}/locations?activo=true`)
      ])
      setSalesProfiles(await profilesRes.json())
      setLocations(await locationsRes.json())
    } catch (error) {
      console.error('Error al cargar datos:', error)
    }
  }
  if (open) loadData()
}, [open])

// 2. Agregar selectores en el formulario (antes de customer_name)
<div>
  <Label htmlFor="sales-profile">Perfil de Venta *</Label>
  <Select value={selectedSalesProfile} onValueChange={setSelectedSalesProfile}>
    <SelectTrigger>
      <SelectValue placeholder="Selecciona perfil" />
    </SelectTrigger>
    <SelectContent>
      {salesProfiles.map((profile) => (
        <SelectItem key={profile.id} value={profile.slug}>
          {profile.nombre} ({profile.tipo})
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>

<div>
  <Label htmlFor="location">Ubicación Origen del Stock *</Label>
  <Select 
    value={selectedLocation?.toString() || ''} 
    onValueChange={(v) => setSelectedLocation(parseInt(v))}
  >
    <SelectTrigger>
      <SelectValue placeholder="Selecciona ubicación" />
    </SelectTrigger>
    <SelectContent>
      {locations.map((location) => (
        <SelectItem key={location.id} value={location.id.toString()}>
          {location.nombre} ({location.tipo})
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>

// 3. Validar stock en la ubicación seleccionada
const validateStockInLocation = async (productId: number, cantidad: number) => {
  if (!selectedLocation) {
    toast.error('Selecciona una ubicación primero')
    return false
  }
  
  try {
    const response = await fetch(`${API_URL}/products/${productId}/stock/by-location`)
    const data = await response.json()
    const stockInLocation = data.items.find((s: any) => s.location_id === selectedLocation)
    
    if (!stockInLocation || stockInLocation.cantidad_disponible < cantidad) {
      toast.error(`Stock insuficiente en ${locations.find(l => l.id === selectedLocation)?.nombre}`)
      return false
    }
    return true
  } catch (error) {
    toast.error('Error al validar stock')
    return false
  }
}

// 4. Al crear la orden, incluir nuevos campos
const orderData: CreateOrderRequest = {
  profile_slug: currentProfile?.slug || '',  // Legacy compatibility
  sales_profile_slug: selectedSalesProfile,   // V2.0
  source_location_id: selectedLocation || undefined,  // V2.0
  customer_name: customerName,
  customer_phone: customerPhone,
  canal,
  metodo_pago: metodoPago,
  items: selectedProducts.map(p => ({
    product_id: p.product_id,
    cantidad: p.cantidad
  }))
}
```

---

### 6. Actualizar `ProductCard.tsx`

**Objetivo:** Mostrar stock total y permitir ver desglose por ubicación.

**Cambios necesarios:**

```typescript
// 1. Agregar botón para ver stock por ubicación
<Button
  variant="outline"
  size="sm"
  onClick={() => handleViewStockByLocation(product.id)}
>
  Ver Stock por Ubicación
</Button>

// 2. Crear diálogo para mostrar stock por ubicación
const [showStockBreakdown, setShowStockBreakdown] = useState(false)
const [stockByLocation, setStockByLocation] = useState<StockByLocation[]>([])

const handleViewStockByLocation = async (productId: number) => {
  try {
    const response = await fetch(`${API_URL}/products/${productId}/stock/by-location`)
    const data = await response.json()
    setStockByLocation(data.items || [])
    setShowStockBreakdown(true)
  } catch (error) {
    toast.error('Error al cargar stock')
  }
}

// 3. Diálogo de desglose
<Dialog open={showStockBreakdown} onOpenChange={setShowStockBreakdown}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Stock por Ubicación</DialogTitle>
    </DialogHeader>
    <div className="space-y-2">
      {stockByLocation.map((stock) => (
        <div key={stock.location_id} className="flex justify-between border-b py-2">
          <span>{stock.location?.nombre || `Ubicación ${stock.location_id}`}</span>
          <Badge>{stock.cantidad_disponible} unidades</Badge>
        </div>
      ))}
      <div className="flex justify-between font-bold pt-2">
        <span>Total:</span>
        <span>{stockByLocation.reduce((sum, s) => sum + s.cantidad_disponible, 0)} unidades</span>
      </div>
    </div>
  </DialogContent>
</Dialog>
```

---

### 7. Actualizar `OrderCard.tsx`

**Objetivo:** Mostrar perfil de venta y ubicación en las órdenes.

**Cambios necesarios:**

```typescript
// 1. Cargar datos relacionados si existen IDs
const [salesProfile, setSalesProfile] = useState<SalesProfile | null>(null)
const [sourceLocation, setSourceLocation] = useState<Location | null>(null)

useEffect(() => {
  const loadRelatedData = async () => {
    if (order.sales_profile_id) {
      const response = await fetch(`${API_URL}/sales-profiles/${order.sales_profile_id}`)
      setSalesProfile(await response.json())
    }
    if (order.source_location_id) {
      const response = await fetch(`${API_URL}/locations/${order.source_location_id}`)
      setSourceLocation(await response.json())
    }
  }
  loadRelatedData()
}, [order])

// 2. Mostrar información V2.0
{salesProfile && (
  <div className="flex items-center gap-2 text-sm">
    <Robot className="w-4 h-4" />
    <span>Vendido por: {salesProfile.nombre}</span>
  </div>
)}

{sourceLocation && (
  <div className="flex items-center gap-2 text-sm">
    <MapPin className="w-4 h-4" />
    <span>Stock de: {sourceLocation.nombre}</span>
  </div>
)}
```

---

### 8. Actualizar `DashboardStats.tsx`

**Objetivo:** Agregar métricas por ubicación y por perfil de venta.

**Cambios necesarios:**

```typescript
// 1. Agregar tabs para ver métricas por ubicación y por perfil
<Tabs defaultValue="general">
  <TabsList>
    <TabsTrigger value="general">General</TabsTrigger>
    <TabsTrigger value="por-ubicacion">Por Ubicación</TabsTrigger>
    <TabsTrigger value="por-perfil">Por Perfil de Venta</TabsTrigger>
  </TabsList>
  
  <TabsContent value="general">
    {/* Métricas actuales */}
  </TabsContent>
  
  <TabsContent value="por-ubicacion">
    {/* Gráfico de stock por ubicación */}
    {/* Top ubicaciones por ventas */}
  </TabsContent>
  
  <TabsContent value="por-perfil">
    {/* Rendimiento de cada bot/vendedor */}
    {/* Ventas por perfil */}
  </TabsContent>
</Tabs>
```

---

## 🔧 Servicios API a Actualizar

### `src/lib/apiClient.ts` o servicio de productos

Agregar métodos:

```typescript
// Stock por ubicación
async getProductStockByLocation(productId: number) {
  return fetch(`${this.baseURL}/products/${productId}/stock/by-location`)
}

async setProductStockAtLocation(productId: number, locationId: number, cantidad: number) {
  return fetch(`${this.baseURL}/products/${productId}/stock/location/${locationId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cantidad })
  })
}

// Ubicaciones
async getLocations(filters?: { tipo?: string; activo?: boolean }) {
  const params = new URLSearchParams(filters as any)
  return fetch(`${this.baseURL}/locations?${params}`)
}

async createLocation(data: Omit<Location, 'id' | 'created_at'>) {
  return fetch(`${this.baseURL}/locations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
}

// Perfiles de venta
async getSalesProfiles(filters?: { tipo?: string; activo?: boolean }) {
  const params = new URLSearchParams(filters as any)
  return fetch(`${this.baseURL}/sales-profiles?${params}`)
}

async createSalesProfile(data: Omit<SalesProfile, 'id' | 'slug' | 'created_at'>) {
  return fetch(`${this.baseURL}/sales-profiles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
}
```

---

## 📋 Checklist de Integración

### Componentes Base (✅ Completados)
- [x] `LocationsList.tsx`
- [x] `SalesProfilesList.tsx`
- [x] Tipos TypeScript actualizados
- [x] App.tsx con nuevas pestañas

### Componentes a Actualizar (⏳ Pendientes)
- [ ] `NewProductDialog.tsx` - Stock por ubicación
- [ ] `EditProductDialog.tsx` - Editar stock por ubicación
- [ ] `NewOrderDialog.tsx` - Selección de perfil y ubicación
- [ ] `ProductCard.tsx` - Ver desglose de stock
- [ ] `OrderCard.tsx` - Mostrar perfil y ubicación
- [ ] `DashboardStats.tsx` - Métricas por ubicación/perfil

### Nuevos Componentes Opcionales
- [ ] `StockByLocationDialog.tsx` - Diálogo reutilizable para ver/editar stock
- [ ] `LocationSelector.tsx` - Selector reutilizable de ubicaciones
- [ ] `SalesProfileSelector.tsx` - Selector reutilizable de perfiles

---

## 🚀 Prioridad de Implementación

**Alta Prioridad (Funcionalidad básica):**
1. `NewOrderDialog` - Crítico para crear órdenes con V2.0
2. `EditProductDialog` - Necesario para gestionar stock
3. `ProductCard` - Mostrar stock por ubicación

**Media Prioridad (UX mejorada):**
4. `NewProductDialog` - Asignar stock inicial
5. `OrderCard` - Mostrar trazabilidad
6. `DashboardStats` - Métricas avanzadas

**Baja Prioridad (Optimizaciones):**
7. Componentes reutilizables
8. Animaciones y transiciones
9. Exportación de reportes por ubicación

---

## 📚 Documentación de Referencia

- **Backend API:** Ver `api-examples-nuevo-sistema.json`
- **Arquitectura:** Ver `NUEVO_SISTEMA_UBICACIONES.md`
- **Tipos:** Ver `src/lib/types.ts`
- **Estado:** Ver `ESTADO_SISTEMA_V2.md`
