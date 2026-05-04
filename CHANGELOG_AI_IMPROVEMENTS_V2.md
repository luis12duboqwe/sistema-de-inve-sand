# Mejoras de IA y Sistema de Solicitud de Fotos v2.0

**Fecha:** Marzo 10, 2026  
**Estado:** ✅ Implementado y validado  
**Commits Pending:** Incluir script migración + este resumen

## 📋 Cambios Implementados

### I. Modelo de Datos Extendido

#### `backend/app/models/ai.py` - Memoria del Cliente
Agregadas 7 columnas a la entidad `Customer`:
- `conversation_summary: str | None` - Resumen ejecutivo de conversaciones anteriores
- `ai_memory_json: str | None` - Blob JSON con contexto extraído de interacciones
- `last_referenced_product_id: int | None` - ID último producto mencionado por cliente
- `last_referenced_product_name: str | None` - Nombre legible del producto
- `last_referenced_color: str | None` - Color/variante última mencionada
- `last_referenced_variant: str | None` - Variante/tamaño última mencionada
- `memory_updated_at: datetime | None` - Timestamp última actualización de memoria

**Propósito:** Permitir que el IA reaccione *antes* de invocar GPT, usando memoria heurística en lugar de solo historial reciente. Reduce latencia y mejora consistencia.

#### `backend/app/models/photos.py` - Cola de Solicitudes Enriquecida
Agregadas 5 columnas a `PhotoRequest`:
- `customer_name: str | None` - Nombre legible del cliente
- `origin_channel: str | None` - Canal (whatsapp, facebook, instagram)
- `claimed_at: datetime | None` - Cuándo un agente reclamó la solicitud
- `last_notified_at: datetime | None` - Última vez notificado al agente
- `notification_count: int` - Cuántas veces se notificó (SLA tracking)

**Propósito:** Operacionalizar la cola. Los agentes saben quién pidió qué, de dónde, y cuánto tiempo ha esperado.

### II. Esquemas Pydantic Extendidos

#### `backend/app/schemas/ai.py`
- Extendida `AICustomerResponse` con campos memoria del cliente
- Permite que lista de clientes exponga contexto de memoria para decisiones en Frontend

#### `backend/app/schemas/photos.py`
- Extendida `PhotoRequestCreate` con `customer_name`, `origin_channel`
- Extendida `PhotoRequestResponse` con prioridad, SLA, metadata de cola
- Nueva `PhotoRequestSummaryResponse` para resumen de contador pendiente

### III. Backend: Orquestación de IA Mejorada

#### `backend/app/routers/ai_intelligence.py` - Core Inteligencia

**Nuevas funciones auxiliares:**
- `_extract_search_keywords()` - Parsea request del cliente para búsqueda
- `_parse_customer_memory()` - Deserializa JSON de memoria heurística
- `_save_customer_memory()` - Persiste memoria actualizada a BD
- `_infer_customer_intent()` - Clasifica básicamente si es búsqueda/consulta/compra  
- `_find_candidate_products()` - Búsqueda determinística en catálogo (antes de GPT)
- `_retrieve_semantic_memory_snippets()` - Recupera fragmentos de `InteractionLog` relevantes por overlap de palabras clave
- `_build_customer_memory_summary()` - Sintetiza memoria en texto de contexto
- `_update_customer_memory()` - Post-interacción: actualiza memoria con info nueva

**Cambios a funciones existentes:**
- `get_ai_context()` - Ahora incluye:
  - Resumen de memoria heurística del cliente
  - Fragmentos semánticos de interacciones previas
  - Último producto/color/variante referenciado
  - Contexto más rico para reducir necesidad de prompt perfecto
  
- `generate_ai_reply()` - Ahora actualiza memoria del cliente **después** de responder
  
- `handle_message_without_n8n()` - Ahora:
  - Usa `_find_candidate_products()` para mejor inferencia en solicitudes de fotos
  - Persiste memoria  
  - Enriquece `PhotoRequest` creada con metadatos de cola

- `list_customers_ai()` - Expone memoria en respuesta para admin

### IV. Sistema de Solicitudes de Fotos con Cola Operativa

#### `backend/app/routers/photo_requests.py` - Full Lifecycle

**Nuevas funciones:**
- `_compute_priority_score()` - Calcula urgencia (tiempo, notificaciones)
- `_is_sla_breached()` - Si solicitud esperó >2 horas sin asignar
- `_serialize_photo_request_detail()` - Serialización enriquecida con prioridad/SLA

**Nuevos endpoints:**

1. **`GET /api/photo-requests/summary`**  
   Retorna contador de pendientes por estado: `{pending: N, claimed: N, awaiting_upload: N}`  
   Usado por badge global en UI

2. **`POST /api/photo-requests/{id}/claim`**  
   Login: agente reclama solicitud (set `claimed_at`, actualiza status a `claimed`)  
   Mantiene historial de quién trabajó en qué

3. **`POST /api/photo-requests/{id}/upload-file`**  
   Soporte para upload binario directo (file FormData)  
   Almacena en `/uploads/`, retorna URL accesible

**Cambios a endpoints existentes:**
- `create_photo_request()` - Ahora captura `customer_name`, `origin_channel` automáticamente
- `GET /api/photo-requests/pending` - Ahora:
  - Calcula y retorna `priority_score` y `sla_breached`
  - Ordena por urgencia (SLA first, luego prioridad)
  - Notifica al agente designado (con timestamp/contador)

### V. Montaje de Uploads Estáticos

#### `backend/app/main.py`
- Crea directorio `/uploads` automáticamente en startup
- Monta path estático en `GET /uploads/<filename>` para servir archivos binarios
- **Nota:** En producción, usar S3/CloudFront en lugar de filesystem local

### VI. Cliente API Frontend

#### `src/lib/apiClient.ts` - Nuevos Métodos
- `getPhotoRequestSummary()` - Obtiene contador para badge
- `claimPhotoRequest(id)` - POST claim
- `uploadPhotoFile(id, file)` - FormData upload binario

Todos usan patrón existente (`getApiUrl()`, autenticación por Bearer token).

### VII. Tipos TypeScript

#### `src/lib/types.ts`
- Extendida `Customer` con campos de memoria
- Agregadas `PhotoRequest`, `PhotoRequestMedia`, `PhotoRequestSummary`

### VIII. UI Dashboard de Agente

#### `src/components/PhotoRequestsDashboard.tsx`
- Ahora usa solicitud fresca post-claim/upload (no stale DOM)
- Polling cada 15s de list
- Soporte dual: URL input o file binary upload
- Badges de estado: pending, claimed, awaiting_upload, completed
- Muestra:
  - Nombre de cliente
  - Canal de origen
  - Prioridad/SLA breached
  - Tiempo en cola

#### `src/App.tsx`
- Polling de `getPhotoRequestSummary()` cada 15s
- Badge contador sobre botón de solicitudes (actualizado en tiempo real)

### IX. Migración de Base de Datos

#### `backend/migrate_add_ai_memory_and_queue.py`
- Script idempotente que agrega colonas si no existen
- Intended para ejecutar en deployments existentes
- No rompe si BD ya está actualizada

## 🎯 Resultados

### Mejoras de IA
✅ **Antes:** Bot dependía 100% de system_prompt + historial corto  
✅ **Ahora:** Bot usa memoria heurística, inferencia de producto pre-GPT, contexto semántico

### Operacionalización de Fotos
✅ **Antes:** "Pedir foto" → chat abierto sinidentidad/urgencia  
✅ **Ahora:** Queue estructurada con prioridad, SLA, tracking de notificaciones, agente asignado

### Upload Binario
✅ **Antes:** Solo URL copy-paste  
✅ **Ahora:** Drag-and-drop file directo con almacenamiento local

### Visibilidad
✅ Badge global muestra solicitudes pendientes  
✅ Agente ve prioridad, canal, cliente, SLA en una lista ordenada

## 🧪 Validación

```bash
# Backend
✅ 50 tests passed in 6.28s
✅ Python compile OK

# Frontend
✅ npm run build succeeded
  - 8587 modules transformed
  - dist/assets generated successfully
```

## 📝 Próximos Pasos Opcionales

1. **ML-Powered Photo Suggestion**  
   Detectar automáticamente qué productos podría el cliente querer (basado en memory)

2. **Push Notifications**  
   Notificar agente por WhatsApp/browser push cuando foto se pida (en lugar de solo polling)

3. **Auto-Response Template para Fotos**  
   AI envía automáticamente un "Perfecto, dame un momento..." mientras agente trabaja

4. **Histórico de Fotos por Producto**  
   Galería persistente de fotos de cada artículo para reutilización

5. **Integration con Storage Externo**  
   S3/Cloudinary en lugar de `/uploads` local para producción

## ⚙️ Configuración Recomendada

Para activar todas las mejoras, asegurarse de:
1. Usar API mode (no local KV)
2. Ejecutar migración: `python3 migrate_add_ai_memory_and_queue.py`
3. Reiniciar backend (para montar `/uploads`)
4. Agentes verán badge de fotos pendientes automáticamente

---

**Implementado por:** GitHub Copilot  
**Líneas de código:** ~400 nuevas funciones + endpoints + componentes UI  
**Feedback:** El sistema ahora es operacionalmente consciente, no solo conversacional.
