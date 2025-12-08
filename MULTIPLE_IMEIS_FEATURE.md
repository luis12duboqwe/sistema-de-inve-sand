# Mejora Implementada: Múltiples IMEIs por Producto

## 📋 Problema Solucionado

Anteriormente, cuando agregabas un producto con stock de 5 unidades, solo podías registrar 1 IMEI. Esto era un problema porque cada celular tiene su propio IMEI único.

## ✅ Solución Implementada

Ahora el sistema permite registrar un IMEI diferente para cada unidad en stock:

### Frontend

1. **NewProductDialog.tsx**
   - Campo IMEI cambió de un solo input a múltiples inputs dinámicos
   - Se crean automáticamente tantos campos IMEI como unidades de stock
   - Si cambias el stock de 1 a 5, aparecen 5 campos IMEI
   - Cada campo está etiquetado como "Unidad 1", "Unidad 2", etc.

2. **ProductCard.tsx**
   - Muestra todos los IMEIs disponibles del producto
   - Los IMEIs se visualizan como badges con fuente monospace
   - Solo muestra IMEIs de unidades no vendidas

3. **Tipos TypeScript** (`types.ts`)
   - Agregado campo `imeis?: string[]` al interface Product
   - Mantiene `imei?: string` por compatibilidad con datos antiguos

### Backend

1. **Modelo de Datos** (`models.py`)
   - Nueva tabla `ProductIMEI` para almacenar múltiples IMEIs
   - Campos:
     - `product_id`: Relación con el producto
     - `imei`: IMEI único (con índice)
     - `vendido`: Boolean para marcar si fue vendido
     - `order_id`: Referencia a la orden si fue vendido
     - `created_at`: Fecha de registro

2. **Schemas** (`schemas.py`)
   - `ProductBase`: Agregado campo `imeis: Optional[List[str]]`
   - `ProductUpdate`: Agregado campo `imeis: Optional[List[str]]`
   - `ProductResponse`: Agregado campo `imeis: Optional[List[str]]`

3. **Router de Productos** (`routers/products.py`)
   - `create_product()`: 
     - Valida que cada IMEI sea único
     - Crea registros en `ProductIMEI` por cada IMEI
     - Retorna error 400 si un IMEI ya existe
   - `_serialize_product()`:
     - Incluye lista de IMEIs disponibles (no vendidos)

4. **Migración** (`migrate_product_imeis.py`)
   - Crea tabla `product_imeis`
   - Migra IMEIs existentes de la columna `imei` a la nueva tabla
   - Mantiene la columna antigua por compatibilidad

## 🚀 Cómo Usar

### Al crear un producto nuevo:

1. Selecciona categoría "Celular"
2. Ingresa el stock inicial (ej: 5 unidades)
3. Automáticamente aparecerán 5 campos para IMEI
4. Ingresa el IMEI de cada unidad (opcional)
5. Al guardar, todos los IMEIs se registran en la base de datos

### Validaciones:

- ✅ Cada IMEI debe ser único en todo el sistema
- ✅ Si intentas registrar un IMEI duplicado, recibirás un error
- ✅ Los campos IMEI son opcionales (puedes dejar algunos vacíos)
- ✅ Solo se guardan los IMEIs que tienen valor

### Al ver un producto:

- Los IMEIs disponibles se muestran en el ProductCard
- Se visualizan como badges azules con fuente monospace
- Solo se muestran IMEIs de unidades no vendidas

## 📝 Migración de Datos

Para aplicar los cambios en la base de datos:

```bash
cd backend
python3 migrate_product_imeis.py
```

La migración:
1. Crea la tabla `product_imeis`
2. Migra IMEIs existentes automáticamente
3. Mantiene compatibilidad con datos antiguos

## 🔄 Compatibilidad

- ✅ Productos antiguos con `imei` siguen funcionando
- ✅ Nuevos productos usan `imeis[]` (array)
- ✅ El frontend detecta automáticamente qué campo usar
- ✅ El backend acepta ambos formatos

## 🎯 Beneficios

1. **Trazabilidad completa**: Cada celular tiene su IMEI único registrado
2. **Control de inventario**: Sabes exactamente qué IMEIs están disponibles
3. **Gestión de ventas**: Puedes marcar qué IMEI se vendió en cada orden
4. **Garantías**: Registro preciso para reclamos de garantía
5. **Prevención de fraudes**: Detecta duplicados automáticamente

## 📊 Próximas Mejoras Sugeridas

- [ ] Al vender un producto, permitir seleccionar qué IMEI específico se vende
- [ ] Mostrar en el detalle de orden qué IMEI se vendió
- [ ] Reportes de IMEIs vendidos vs disponibles
- [ ] Búsqueda por IMEI en el sistema
- [ ] Historial de IMEI (cuándo se registró, cuándo se vendió, a quién)
