# Fix: Error "Failed to fetch" en /profiles

## Problema Identificado

El error `TypeError: Failed to fetch` ocurría al intentar crear un nuevo perfil porque:

1. El frontend intentaba conectarse al backend antes de que estuviera completamente listo
2. No había manejo de reintentos automáticos para errores de red
3. Los mensajes de error no eran descriptivos para el usuario

## Solución Implementada

### 1. Reintentos Automáticos en ApiClient (`src/lib/apiClient.ts`)

- **Agregado**: Sistema de reintentos con 3 intentos automáticos
- **Espera progresiva**: 500ms, 1000ms, 1500ms entre reintentos
- **Detección inteligente**: Solo reintenta en errores de red (`Failed to fetch`)
- **Mensajes mejorados**: Errores descriptivos con instrucciones para el usuario

```typescript
private async request<T>(
  endpoint: string,
  options: RequestInit = {},
  retries = 3  // ← Nuevo parámetro
): Promise<T>
```

### 2. Verificación de Conexión al Inicio (`src/components/BackendConnectionCheck.tsx`)

- **Nuevo componente**: Verifica la conexión del backend antes de cargar la aplicación
- **UI informativa**: Muestra estado de conexión con indicadores visuales
- **Reintentos manuales**: Botón para reintentar la conexión si falla
- **Instrucciones claras**: Muestra comandos para iniciar el backend si no está corriendo

### 3. Integración en App.tsx

- **Verificación temprana**: Se ejecuta antes de cargar cualquier dato
- **Flujo mejorado**: No se carga la aplicación hasta confirmar que el backend está disponible
- **Estado gestionado**: Variable `backendConnected` controla el flujo de la aplicación

## Cambios de Código

### Archivo 1: `src/lib/apiClient.ts`
- ✅ Agregado sistema de reintentos automáticos
- ✅ Mensajes de error descriptivos con contexto
- ✅ Detección específica de errores de red

### Archivo 2: `src/components/BackendConnectionCheck.tsx` (NUEVO)
- ✅ Componente de verificación de conexión
- ✅ UI con loader, mensajes de error y éxito
- ✅ Botón de reintento manual
- ✅ Instrucciones para iniciar el backend

### Archivo 3: `src/App.tsx`
- ✅ Importado componente `BackendConnectionCheck`
- ✅ Agregado estado `backendConnected`
- ✅ Renderizado condicional para verificar conexión primero

## Cómo Funciona

1. **Al cargar la aplicación**:
   - Se muestra el componente `BackendConnectionCheck`
   - Se verifica conexión a `http://localhost:8000/api/profiles`

2. **Si el backend está disponible**:
   - Se muestra mensaje de éxito
   - Se establece `backendConnected = true`
   - Se carga la aplicación normalmente

3. **Si el backend NO está disponible**:
   - Se muestra alerta con error descriptivo
   - Se proporcionan instrucciones para iniciar el backend
   - Usuario puede reintentar cuando esté listo

4. **Durante operaciones normales**:
   - Cualquier error `Failed to fetch` se reintenta automáticamente 3 veces
   - Si fallan todos los intentos, se muestra mensaje descriptivo

## Verificación

El backend está corriendo correctamente:
```bash
$ curl http://localhost:8000/api/profiles
{"items":[],"total":0,"page":1,"per_page":50,"pages":0}
```

## Beneficios

✅ **Experiencia de usuario mejorada**: Mensajes claros en lugar de errores técnicos
✅ **Mayor robustez**: Manejo automático de problemas de red temporales
✅ **Debugging más fácil**: Logs detallados y mensajes informativos
✅ **Prevención de errores**: Verifica conexión antes de permitir operaciones

## Siguiente Paso

Recarga la aplicación frontend para aplicar los cambios. El componente ahora:
1. Verificará la conexión del backend
2. Manejará errores de red con reintentos automáticos
3. Proporcionará feedback claro al usuario
