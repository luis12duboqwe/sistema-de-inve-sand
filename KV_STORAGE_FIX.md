# Solución al Error "Failed to load profiles: Failed to fetch KV key"

## Problema Identificado

El sistema intentaba usar `window.spark.kv` directamente, pero esta API no estaba disponible o no estaba funcionando correctamente en el entorno, causando el error:

```
Failed to load profiles: Failed to fetch KV key
```

## Solución Implementada

### 1. Capa de Abstracción de Almacenamiento (`kvStorage.ts`)

Se creó un nuevo archivo `/src/lib/kvStorage.ts` que proporciona:

- **Interfaz unificada**: Define `SparkKV` con los métodos `get`, `set`, `delete`, y `keys`
- **Implementación de fallback**: `LocalStorageKV` que usa `localStorage` con prefijo `spark-kv-`
- **Detección automática**: `getKV()` detecta si `window.spark.kv` está disponible y funciona, de lo contrario usa localStorage
- **Singleton pattern**: Una única instancia compartida en toda la aplicación

### 2. Archivos Actualizados

Se actualizaron las siguientes clases/archivos para usar `getKV()`:

1. **`/src/lib/inventoryService.ts`**
   - Todas las operaciones de almacenamiento (profiles, products, stock, orders, order items)
   - 9 reemplazos de `window.spark.kv` por `getKV()`

2. **`/src/lib/apiClient.ts`**
   - Obtención de URL de API desde configuración

3. **`/src/lib/inventoryServiceFactory.ts`**
   - Lectura de configuración de uso de API

4. **`/src/hooks/use-sync-detection.ts`**
   - Detección de cambios de sincronización

### 3. Inicialización de Datos (`dataInitializer.ts`)

Se creó `/src/lib/dataInitializer.ts` con funciones útiles:

- **`initializeDefaultData()`**: Inicializa arrays vacíos si no existen datos
- **`clearAllData()`**: Limpia todos los datos del sistema
- **`exportAllData()`**: Exporta todos los datos a un objeto JSON
- **`importAllData()`**: Importa datos desde un objeto JSON

Estas funciones están disponibles globalmente en `window.inventoryDebug` para debugging.

### 4. Mejora en App.tsx

Se actualizó `App.tsx` para:
- Importar `initializeDefaultData`
- Llamar a la inicialización antes de cargar datos
- Mostrar mensajes de error más claros con `toast.error()`

## Beneficios

✅ **Compatibilidad**: Funciona tanto con `window.spark.kv` como sin él  
✅ **Fallback robusto**: Si Spark KV no está disponible, usa localStorage automáticamente  
✅ **Sin cambios de API**: El código de la aplicación sigue usando la misma interfaz  
✅ **Mejor debugging**: Mensajes de consola claros sobre qué sistema de almacenamiento se está usando  
✅ **Inicialización automática**: Los datos se inicializan correctamente en el primer uso  

## Uso

### Normal
El sistema funciona automáticamente. No requiere configuración adicional.

### Debugging en Consola del Navegador

```javascript
// Verificar qué sistema de almacenamiento se está usando
// (Revisa la consola, debería decir "Using Spark KV storage" o "Using localStorage fallback")

// Herramientas de debugging disponibles
window.inventoryDebug.exportAllData()  // Exportar todos los datos
window.inventoryDebug.clearAllData()   // Limpiar todos los datos (¡cuidado!)
window.inventoryDebug.initializeDefaultData()  // Reinicializar

// Test del sistema KV
window.testKVStorage()  // Ejecuta tests básicos
```

## Verificación

Para verificar que la solución funciona:

1. Abre la aplicación en el navegador
2. Abre la consola del navegador (F12)
3. Busca el mensaje: "Using Spark KV storage" o "Using localStorage fallback"
4. Si ves "Data already initialized" o "Default data initialized successfully", todo está funcionando
5. No deberías ver el error "Failed to load profiles" nuevamente

## Archivos Creados

- `/src/lib/kvStorage.ts` - Capa de abstracción de almacenamiento
- `/src/lib/kvStorage.test.ts` - Tests manuales del sistema KV
- `/src/lib/dataInitializer.ts` - Utilidades de inicialización y manejo de datos
- `/docs/KV_STORAGE_FIX.md` - Este documento

## Archivos Modificados

- `/src/lib/inventoryService.ts`
- `/src/lib/apiClient.ts`
- `/src/lib/inventoryServiceFactory.ts`
- `/src/hooks/use-sync-detection.ts`
- `/src/App.tsx`
