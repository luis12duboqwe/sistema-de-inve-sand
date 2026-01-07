# Estrategia de Sincronización Local → API

## Objetivo
Asegurar que los datos capturados en modo local (Spark KV) se puedan replicar de forma segura y determinista hacia el backend FastAPI en cuanto el usuario reactive el modo API, evitando duplicados y resolviendo conflictos sin bloquear la operación.

## Estado Actual
- El módulo `syncService` solo realiza envíos masivos de perfiles, ubicaciones, sales profiles y productos creando *siempre* registros nuevos mediante `apiClient`.
- No hay noción de qué registros ya se sincronizaron ni manejo de cambios incrementales (actualizaciones, eliminaciones, IMEIs, órdenes, transferencias, etc.).
- No se valida conectividad ni permisos antes de comenzar la sincronización, y tampoco se informa progreso al usuario.

## Principios de Diseño
1. **Registro de cambios (Change Journal):** toda operación que modifique datos en modo local debe generar un evento (`type`, `entity`, `entityId`, `payload`, `timestamp`, `hash`).
2. **Idempotencia:** cada evento tendrá un `uuid` y se marcará como `synced_at` tras confirmación del backend.
3. **Versionado lógico:** los registros locales deben almacenar `updated_at` y `origin` (`local`/`remote`) para detectar conflictos con la última réplica del backend.
4. **Reconciliación explícita:** los conflictos se resuelven con reglas determinísticas (por prioridad de origen, timestamps o intervención manual cuando sea necesario).
5. **Transparencia para el usuario:** la UI mostrará barra de progreso y errores detallados; ninguna sincronización ocurrirá en segundo plano sin consentimiento cuando el tamaño del journal supere un umbral configurable.

## Flujo Propuesto
1. **Detección de modo:** `settings_use_api` cambia a `true` (desde `SettingsDialog`). Antes de recargar, se pregunta si debe iniciarse una sincronización y se almacena la intención en `settings_pending_sync = true`.
2. **Pre-flight:** al iniciar en modo API, `syncOrchestrator` verifica token válido, versión del backend y estampa `sync_session_id`. Si falla, se revierte a modo local.
3. **Carga de journal:** se leen eventos locales agrupados por entidad y acción (create/update/delete). Se ignoran los ya marcados como `synced_at`.
4. **Ejecución:**
   - **Creaciones:** se envían en lotes pequeños (ej. 25) manteniendo orden cronológico. El backend devuelve el `remote_id` y un `checksum`. El local actualiza el registro y marca el evento como sincronizado.
   - **Actualizaciones:** se compara `local.updated_at` vs `remote.updated_at`. Si el remoto es más reciente, se abre conflicto.
   - **Eliminaciones:** se envían `soft deletes` (flag `activo=false`). Solo se ejecutan cuando el `remote.updated_at` ≤ `local.updated_at`.
5. **Conflictos:** se guardan en `sync-conflicts` (KV) con detalles para resolverlos manualmente en un nuevo componente `SyncConflictsDialog`.
6. **Descarga de estado:** tras subir el journal, se solicita un snapshot remoto (productos, stock, IMEIs, órdenes recientes, transfers, perfiles y configuraciones). Se reemplazan los KV locales con la versión oficial y se marca `settings_last_sync_at`.
7. **Eventos en tiempo real:** `useRealtimeSync` escucha `BroadcastChannel` y `storage` para invalidar caches y evitar escribir sobre datos ya sincronizados.

## Componentes a Crear/Actualizar
| Componente | Responsabilidad | Archivos clave |
|------------|-----------------|----------------|
| `syncJournal` util | Guardar/leer eventos y exponer API `recordChange`, `markSynced`, `getPendingEvents` | `src/lib/syncJournal.ts` |
| Instrumentación en servicios | Cada método que muta datos en `inventoryService.ts` registra eventos (ej. `createProduct`, `updateStock`, `assignIMEI`, `createOrder`, etc.) | `src/lib/inventoryService.ts` |
| `syncOrchestrator` | Coordina pre-flight, subida de eventos, descarga de snapshot y resolución de conflictos | `src/lib/syncService.ts` (reestructurado) |
| UI de sincronización | Mostrar progreso, historial, conflictos, botón "Reintentar" | `src/components/SettingsDialog.tsx`, nuevo `SyncProgressDialog.tsx` |
| Estado global | Nuevas claves KV: `sync-pending-events`, `sync-last-session`, `sync-conflicts`, `settings_last_sync_at`, `settings_pending_sync` | `src/lib/kvStorage.ts` |

## Reglas de Resolución de Conflictos
| Caso | Regla | Acción |
|------|-------|--------|
| Registro solo local | Crear en backend, guardar `remote_id` | Automático |
| Ambos modificados | Si `local.updated_at > remote.updated_at + tolerance`, sobrescribir remoto; de lo contrario marcar conflicto | Semi-automático |
| Eliminado en remoto pero editado local | Priorizar remoto, notificar al usuario | Manual |
| IMEI reasignado en ambos lados | Verificar `IMEIHistory`; si difiere, bloquear sincronización y alertar | Manual |

## Manejo de Errores y Reintentos
- Retries exponenciales con jitter para cada lote (máx. 3 intentos). Los eventos fallidos permanecen en el journal con `last_error` y `retry_count`.
- Si el backend responde con 401/403, se aborta la sesión y se solicita reautenticación.
- Una sincronización parcial mantiene bandera `sync_in_progress`. Al volver a modo local se reanuda desde el último lote confirmado.

## Roadmap de Implementación
1. **Infraestructura:** crear `syncJournal`, ampliar `inventoryService` para registrar operaciones (etiquetadas por entidad). Añadir pruebas unitarias básicas para el journal.
2. **Orquestador:** reescribir `syncService.syncLocalToRemote` siguiendo el flujo propuesto y soportando más entidades (órdenes, transferencias, IMEIs, trade-ins, financing, AI configs).
3. **Frontend:** añadir UI de sincronización (dialogs, toasts, badge en Settings). Integrar con `useRealtimeSync` para invalidar caches tras la réplica.
4. **Conflictos:** nueva vista para resolver conflictos pendientes (mostrar payload local vs remoto, permitir elegir versión o duplicar como draft).
5. **Documentación y pruebas:** actualizar `INTEGRATION.md` e `INICIO_RAPIDO.md` para explicar el proceso; agregar scripts manuales de validación.

## Métricas de Éxito
- 0 duplicados al sincronizar datos creados offline y luego online.
- Tiempo medio de sincronización < 2 min para 1 000 eventos.
- Visibilidad total: el usuario siempre sabe cuántos eventos están pendientes y puede reintentar o cancelar.
