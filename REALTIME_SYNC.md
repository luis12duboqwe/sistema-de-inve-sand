# Sincronización Multi-Dispositivo en Tiempo Real

## Descripción General

Stellar Inventory ahora incluye sincronización automática en tiempo real entre múltiples dispositivos. Los cambios realizados en un dispositivo se reflejan automáticamente en todos los demás dispositivos conectados a la misma cuenta.

## Características Principales

### 🔄 Sincronización Automática
- **Detección Instantánea**: Los cambios se detectan y propagan automáticamente
- **Sin Configuración**: Funciona de forma inmediata sin configuración adicional
- **Multi-Dispositivo**: Sincroniza entre computadoras, tablets y teléfonos
- **Persistencia**: Los datos persisten incluso cuando cierras el navegador

### 📊 Indicador de Estado
- **Visualización en Tiempo Real**: Badge en la barra superior muestra el estado de sincronización
- **Estados Visuales**:
  - 🔄 **Sincronizando**: Ícono rotatorio cuando se están sincronizando datos
  - ✓ **Sincronizado**: Marca de verificación cuando todo está actualizado
  - ⚠️ **Error**: Indica si hay problemas de sincronización
- **Información Detallada**: Hover sobre el indicador para ver:
  - Última vez sincronizado
  - ID del dispositivo actual
  - Estado de la conexión

### 🔔 Notificaciones Inteligentes
- **Cambios Remotos**: Notificación toast cuando otro dispositivo realiza cambios
- **Contexto**: Muestra qué tipo de dato cambió (productos, órdenes, perfiles)
- **No Intrusivo**: Solo notifica cambios significativos, no actualizaciones locales

### ⚙️ Configuración Avanzada

Accede a la configuración de sincronización desde:
- **Menú Principal** → Configuración → Sincronización Multi-Dispositivo
- **Atajo de Teclado**: `Alt + S`

#### Opciones Configurables

1. **Sincronización Habilitada**
   - Activa o desactiva la sincronización completamente
   - Útil si prefieres trabajar offline temporalmente

2. **Notificaciones de Sincronización**
   - Controla si quieres recibir alertas de cambios remotos
   - Recomendado: activado para estar al tanto de todos los cambios

3. **Intervalo de Verificación**
   - **1 segundo**: Más rápido, mayor consumo de recursos
   - **2 segundos**: Balance óptimo (recomendado)
   - **5 segundos**: Moderado, ahorra batería
   - **10 segundos**: Más eficiente, menor frecuencia

4. **Resolución Automática de Conflictos**
   - Cuando está activado: Usa siempre el cambio más reciente
   - Cuando está desactivado: Notifica para resolución manual

5. **Limpiar Datos de Sincronización**
   - Reinicia el ID del dispositivo
   - No elimina tus datos, solo el estado de sincronización
   - Útil para solucionar problemas

## Casos de Uso

### Escenario 1: Múltiples Vendedores
```
Vendedor A (Computadora) → Crea una orden
    ↓
[Sincronización Automática]
    ↓
Vendedor B (Tablet) → Ve la orden instantáneamente
```

### Escenario 2: Gestión Remota
```
Gerente (Oficina) → Ajusta precios de productos
    ↓
[Sincronización en Tiempo Real]
    ↓
Vendedor (Tienda) → Precios actualizados automáticamente
```

### Escenario 3: Trabajo Multi-Dispositivo
```
Usuario (Laptop) → Trabaja en casa agregando productos
Usuario (Trabajo) → Continúa donde lo dejó automáticamente
```

## Tecnología Subyacente

### Spark KV System
- Utiliza el sistema de persistencia KV de Spark
- Almacenamiento local con sincronización automática
- Basado en eventos de Storage API del navegador

### Detección de Cambios
1. **Escucha de Eventos**: Monitorea cambios en localStorage
2. **Comparación de Valores**: Detecta cambios reales vs. lecturas
3. **Propagación**: Actualiza la UI cuando se detectan cambios remotos

### Identificación de Dispositivos
- Cada dispositivo genera un ID único persistente
- Formato: `device-{timestamp}-{random}`
- Almacenado en localStorage como `stellar-device-id`

## Resolución de Conflictos

### Estrategia: "Last Write Wins"
Cuando dos dispositivos modifican el mismo dato:
1. El sistema compara las marcas de tiempo
2. Se mantiene el cambio más reciente
3. Se descarta el cambio más antiguo

### Ejemplo
```
Dispositivo A (10:00 AM): Cambia precio a $100
Dispositivo B (10:01 AM): Cambia precio a $120
    ↓
Resultado: Precio final = $120 (más reciente)
```

## Limitaciones y Consideraciones

### Limitaciones Actuales
- **Mismo Usuario**: Sincroniza dispositivos del mismo usuario/navegador
- **Conexión Requerida**: Requiere que los dispositivos estén activos
- **Storage Limits**: Sujeto a límites de localStorage del navegador (típicamente 5-10MB)

### Mejores Prácticas
1. **Mantén Pestañas Activas**: Para mejor sincronización
2. **No Cierres Inmediatamente**: Espera confirmación de sincronización
3. **Verifica el Indicador**: Asegúrate de ver "Sincronizado" antes de cambiar de dispositivo
4. **Resuelve Conflictos Rápido**: Si ves notificaciones de cambios, revísalos

## Monitoreo y Debugging

### Ver Estado de Sincronización
1. Hover sobre el badge de sincronización en la barra superior
2. Verás:
   - Estado actual (Sincronizando/Sincronizado/Error)
   - Última sincronización (hace 2s, 1m, etc.)
   - ID del dispositivo

### Troubleshooting

#### Problema: No sincroniza entre dispositivos
**Soluciones:**
1. Verifica que la sincronización esté habilitada en ambos dispositivos
2. Abre la configuración de sincronización (`Alt + S`)
3. Confirma que ambos dispositivos tienen notificaciones activadas
4. Intenta "Limpiar Datos de Sincronización"

#### Problema: Sincronización lenta
**Soluciones:**
1. Reduce el intervalo de verificación a 1 o 2 segundos
2. Asegúrate de no tener demasiadas pestañas abiertas
3. Verifica la memoria disponible del navegador

#### Problema: Conflictos frecuentes
**Soluciones:**
1. Coordina ediciones entre usuarios
2. Activa "Resolución Automática de Conflictos"
3. Establece horarios de actualización por usuario

## Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Alt + S` | Abrir configuración de sincronización |
| `Ctrl + ,` | Configuración general (incluye sync) |

## Seguridad y Privacidad

### Almacenamiento Local
- Todos los datos se almacenan localmente en tu navegador
- No se envían a servidores externos por defecto
- Encriptación a nivel de navegador

### Identificación
- Los IDs de dispositivo son aleatorios y únicos
- No contienen información personal identificable
- Se pueden regenerar en cualquier momento

## Futuras Mejoras

### En Desarrollo
- [ ] Sincronización entre diferentes usuarios (modo colaborativo)
- [ ] Historial de cambios con reversión
- [ ] Sincronización con backend API
- [ ] Modo offline con cola de sincronización
- [ ] Resolución manual de conflictos con preview

### Sugerencias Bienvenidas
Si tienes ideas para mejorar la sincronización, por favor contáctanos o abre un issue.

## Preguntas Frecuentes

**P: ¿Necesito internet para que funcione?**
R: Sí, los dispositivos deben estar conectados y activos para sincronizar entre ellos.

**P: ¿Puedo desactivar la sincronización?**
R: Sí, desde Configuración → Sincronización Multi-Dispositivo, desactiva el switch principal.

**P: ¿Qué pasa si dos personas editan lo mismo al mismo tiempo?**
R: El sistema usa "Last Write Wins" - el cambio más reciente prevalece. Puedes desactivar la resolución automática para recibir notificaciones.

**P: ¿Se pierden datos durante la sincronización?**
R: No, la sincronización solo actualiza datos, nunca los elimina sin tu acción explícita.

**P: ¿Funciona con el backend API?**
R: Actualmente la sincronización es independiente del backend API. Si usas el backend, las actualizaciones se reflejan al recargar.

## Soporte

Para problemas o preguntas sobre la sincronización:
1. Revisa esta documentación
2. Verifica el indicador de estado
3. Prueba "Limpiar Datos de Sincronización"
4. Contacta al equipo de soporte técnico

---

**Versión**: 1.0.0  
**Última Actualización**: 2024  
**Estado**: ✅ Producción
