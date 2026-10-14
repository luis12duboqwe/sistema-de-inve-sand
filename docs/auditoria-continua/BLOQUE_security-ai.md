# Auditoría Auth / IA / Canales / Analytics

SHA: dba6763391d12c6c91c9904cba36725710f9280a

Estado: SOLO LECTURA, revisión estática. Sin tests ni servicios reales.

## Prioridad y hallazgos

### SEC-AI-001 — ALTA — JWT sin permiso IA accede a conversaciones e inventario global

CONFIRMADO POR CÓDIGO

Evidencia: backend/app/routers/ai_intelligence.py:444-459 acepta cualquier usuario activo; backend/app/routers/ai_slug_integrity.py:56-72 delega context sin autorización adicional; backend/app/routers/ai_intelligence.py:1111-1149 selecciona cliente por teléfono suministrado; 1176-1304 stock sin scope; 1400-1403 historial sin perfil; 1490-1522 devuelve memoria e historial

Reproducción estática: Usuario Invitado activo, o usuario limitado a tienda A, POST /api/ai/context con slug válido y teléfono de cliente B. Obtiene previous_context, ai_memory, admin_phone e inventario exacto de otras ubicaciones; no requiere OpenAI.

Recomendación: Separar credencial de integración acotada por perfil/canal de JWT staff; exigir permiso IA y acceso cliente/perfil/ubicación. Filtrar todos los recuperadores y limitar datos de respuesta.

Tests propuestos (NO ejecutados): Negativos Invitado sin ai:manage, usuario scope A frente B, teléfono ajeno y perfil diferente; verificar 403 y no mutaciones.

### SEC-AI-002 — ALTA — Creación de ventas por IA omite orders:create

CONFIRMADO POR CÓDIGO

Evidencia: backend/app/routers/ai_intelligence.py:2223-2229 depende solo _require_ai_integration_auth; backend/app/routers/ai_intelligence.py:2146-2197 solo valida ubicación para JWT; backend/app/services/order_service.py:159-245 no verifica permiso orders:create; backend/app/utils/location_access.py:7-28 permite todas ubicaciones a roles sistema sin filas explícitas

Reproducción estática: JWT Invitado activo sin orders:create y sin filas UserLocationAccess; POST /api/ai/create-order con perfil válido, ubicación e item con stock no serializado. Pasa RBAC y llega a venta/stock. Incluso cuenta sin rol con can_edit explícito pasa.

Recomendación: Para JWT exigir orders:create además de can_edit; para servicio acotar perfiles y ubicaciones autorizadas. Aplicar el mismo guard a order_intent de handle-message.

Tests propuestos (NO ejecutados): Prueba DB PostgreSQL con Invitado y stock: 403, stock/órdenes inmutables; mismo caso vía order_intent.

### SEC-AI-003 — ALTA — Respuesta duplicada puede pertenecer a otro cliente

CONFIRMADO POR CÓDIGO

Evidencia: backend/app/routers/ai_intelligence.py:2245-2269 latest_assistant filtra sales_profile_id y role, no customer_id ni message_id

Reproducción estática: Procesar mensaje A con ID M; luego cliente B genera última respuesta en mismo perfil; reintentar M como A. reply devuelve contenido de B. Puede provocarse con payload message_id arbitrario conocido.

Recomendación: Persistir respuesta vinculada a clave mensaje/canal/cuenta/cliente y devolver solo esa respuesta; jamás fallback al último assistant del perfil.

Tests propuestos (NO ejecutados): Dos clientes intercalados y retries; assert reply de A y ausencia texto de B. test_ai_workflow.py:481-512 solo cubre mismo cliente.

### SEC-AI-004 — ALTA — Pronóstico rápido evade restricción por ubicación

CONFIRMADO POR CÓDIGO

Evidencia: backend/app/routers/forecasting.py:14-28 recibe location_id libre y no usa current_user para scope; backend/app/services/forecasting_service.py:26-29 location_id sustituye scope; 64-106 stock/ventas se consultan globalmente si omitido

Reproducción estática: Usuario reports:view limitado a A solicita /api/forecasting/predict?location_id=B o sin filtro; obtiene stock exacto y demanda de B/global.

Recomendación: Alinear con analytics/forecast: validar ubicación y require_location_access, aplicar location_ids accesibles por defecto.

Tests propuestos (NO ejecutados): Usuario scoped A: B 403; sin filtro solo A; no filas acceso retorna vacío para roles custom.

### CH-001 — ALTA — Corrección de webhook no cubre idempotencia del endpoint IA ni limpieza compartida

CONFIRMADO POR CÓDIGO

Evidencia: backend/app/routers/channel_webhook_integrity.py:34-99,360-470 recupera pending_delivery y release de fallos; backend/app/routers/ai_intelligence.py:493-530 elimina todo registro expirado y commit previo a procesamiento; backend/app/routers/ai_intelligence.py:2245-2269 no libera reclamo ante fallo posterior

Reproducción estática: A) /api/ai/handle-message con message_id: fallo get_ai_context/OpenAI/order y retry: duplicate-guard sin completar efecto. B) insertar pending_delivery/manual_recovery expirado; cualquier handle-message nuevo con ID ejecuta cleanup y borra respuesta de recuperación; retry webhook vuelve a IA.

Recomendación: Unificar protocolo de deduplicación y limpieza; preservar estados ambiguos/delivery pendientes en TODOS consumidores. Persistir estado/resultado y decidir recovery antes de replay.

Tests propuestos (NO ejecutados): PostgreSQL fallo antes/después de side effects + retry IA; fila pending_delivery/manual_recovery expirada sobrevive limpieza IA; retry no repite órdenes/fotos.

### CH-005 — MEDIA — n8n sigue con contrato training inválido y sin entrega Meta

CONFIRMADO POR CÓDIGO

Evidencia: docs/n8n/whatsapp_ai_flow.json: nodo Enviar a Cola POST /api/ai/training-queue con sales_profile_id/question/original_answer; backend/app/routers/ai_intelligence.py:1681-1698 ruta POST real /training/submit; 1721-1725 training-queue solo GET; docs/n8n/whatsapp_ai_flow.json: Responder WhatsApp es respondToWebhook, no nodo Meta Graph; docs/INTEGRACION_N8N.md: contratos contradictorios context/log/training

Reproducción estática: Importar plantilla; rama entrenamiento llama método inexistente (405); response webhook por sí misma no envía mensaje Graph. No se verificó ejecución n8n ni puente externo que transforme respuesta.

Recomendación: Definir ruta oficial nativa vs puente n8n, corregir endpoint/esquema y referencia datos del webhook tras HTTP request; añadir envío real o documentar adaptador.

Tests propuestos (NO ejecutados): Staging sin clientes reales: contrato entrada-context-reply-training-entrega y retry; verificar nodo Meta simulado.

### CH-006 — MEDIA — Clave deduplicación global sin cuenta/canal/cliente

RIESGO DE DISEÑO CONFIRMADO; COLISIÓN REAL NO VERIFICADA

Evidencia: backend/app/models/ai.py:102-106 message_id unique global; backend/app/routers/channel_webhook_integrity.py:71-81 lookup solo ID; backend/app/routers/channel_webhook_integrity.py:277-321 cached_delivery_context y envío usan event.channel/customer_id sin cotejar claim.customer_phone/channel

Reproducción estática: Colisión ID en dos canales/cuentas: segundo mensaje se omite; si primero pending_delivery, segunda entrega puede reutilizar su respuesta al recipient del segundo evento. Factibilidad de colisión real Meta no demostrada; API IA permite IDs libres.

Recomendación: Clave compuesta canal/cuenta/message_id, enlazar recipient/profile inmutable y validar reintento. Separar namespace IDs IA/nativos.

Tests propuestos (NO ejecutados): Mismo ID distintos canales/cuentas/customer: no omisión ni reenvío cruzado.

### PHOTO-001 — MEDIA — Fotos ignoran canal de origen persistido

CONFIRMADO POR CÓDIGO

Evidencia: backend/app/routers/photo_requests.py:147 guarda origin_channel; backend/app/routers/photo_requests.py:245-256 resolver usa notas/primer canal y omite origin_channel; backend/app/routers/channel_webhook_integrity.py:259-266 construye payload sin channel_hint; backend/app/routers/ai_intelligence.py:2283-2297 infiere primer canal perfil para solicitud

Reproducción estática: Perfil canales [whatsapp,instagram], solicitud origin_channel=instagram sin notas especiales: envío selecciona whatsapp. En webhook Instagram la IA también infiere WhatsApp.

Recomendación: Propagar canal/cuenta reales desde IncomingEvent y resolver primero origin_channel validado; conservar account context para entrega.

Tests propuestos (NO ejecutados): Perfil multicanal: solicitudes IG/Messenger salen por canal/cuenta originales.

### PHOTO-002 — MEDIA — Envío de lote de fotos no es reintentable sin duplicados

CONFIRMADO POR CÓDIGO

Evidencia: backend/app/routers/photo_requests.py:690-695 selecciona media sin lock; backend/app/routers/photo_requests.py:734-757 y 775-795 envía media secuencial y caption; backend/app/routers/photo_requests.py:804-826 marca todos después de todas entregas

Reproducción estática: Dos media: primera aceptada, segunda/caption falla. Todas quedan unsent; retry reenvía primera. Dos llamadas concurrentes ven mismo lote y entregan dos veces.

Recomendación: Reclamo transaccional/outbox por media y guardar ID/estado de entrega inmediatamente; cuarentena de resultados ambiguos, concurrencia e idempotencia.

Tests propuestos (NO ejecutados): Mock Meta acepta media1 y falla media2/caption; retry solo pendiente. Dos solicitudes concurrentes PostgreSQL no duplican.

### AN-001 — MEDIA — Analytics y forecast usan fecha creación en lugar de fecha venta

CONFIRMADO POR CÓDIGO

Evidencia: backend/app/routers/analytics.py:92-114 usa Order.created_at y <= last_month_end (date a medianoche); backend/app/services/forecasting_service.py:109-125 usa Order.created_at; backend/app/routers/ai_business_integrity.py:101-112 usa effective_sale_column, contraparte ya canónica

Reproducción estática: Orden pendiente creada hace 2 meses y completada hoy: no computa venta actual en analytics/forecast. Venta último día mes a 12:00 queda fuera revenue_last_month.

Recomendación: Usar effective_sale_column/at, ventanas [inicio, siguiente_inicio) y acordar moneda/refunds con reportes canónicos.

Tests propuestos (NO ejecutados): Venta validada posterior creación; último día mes mediodía y límite siguiente mes; reconciliación con reportes.

### AN-002 — MEDIA — Cache forecast ignora parámetros y caducidad

CONFIRMADO POR CÓDIGO

Evidencia: backend/app/routers/analytics.py:149-162 cacheable no considera days_history ni limit y retorna summary tal cual; backend/app/routers/analytics.py:177-183 cache almacena resultado ya truncado; backend/app/jobs/forecasting_job.py:32-40 precalcula 90 días sin metadato days_history

Reproducción estática: Consulta history60 limit1 precarga cache; siguiente history365 limit200 devuelve summary limit1/history60. Sin scheduler, cache permanece hasta restart o force_refresh.

Recomendación: Clave por filtros/history/scope, cache objeto completo y aplicar limit por solicitud, TTL explícito.

Tests propuestos (NO ejecutados): Requests history/limit distintos devuelven datos propios; avance reloj invalida cache.

### AUTH-001 — MEDIA — Cambiar contraseña no invalida JWT anterior

CONFIRMADO POR CÓDIGO

Evidencia: backend/app/auth.py:44-87 JWT valida sub/exp y usuario activo; backend/app/routers/auth_router.py:453-454 y 580-581 cambia hash sin token version

Reproducción estática: Token robado válido; usuario/admin cambia contraseña; JWT anterior sigue autorizado hasta exp. Si username antiguo se reutiliza en otra cuenta, sub puede apuntar a nueva identidad.

Recomendación: JWT con subject ID estable y token_version/password_changed_at; revocar sesiones tras cambio/reset contraseña.

Tests propuestos (NO ejecutados): Token anterior rechazado tras reset; reutilizar username no migra identidad.

## Continuidad PR146

CH-001: PARCIALMENTE REMEDIADO en webhook canónico; vigente vía IA y limpieza compartida (hallazgo actual).

CH-002: IMPLEMENTED: handler canónico Meta Graph facebook v23; legacy se retira. Sin prueba ejecutada ni Meta real.

CH-003: IMPLEMENTED: canónico usa page_access_token en IG como health/send. Sin prueba ejecutada.

CH-004: IMPLEMENTED: BusinessIntegrityMiddleware bloquea producción sin META_APP_SECRET. Legacy sigue fail-open dev; DEBUG=true hace is_production falso, riesgo configuración no observado.

CH-005: VIGENTE (hallazgo actual).

CH-006: VIGENTE, diseño sin separación y retry recipient no cotejado.

## Cobertura

Lecturas completas de fuente: backend/app/auth.py, backend/app/config.py, backend/app/config_production.py, backend/app/crypto.py, backend/app/main.py, backend/app/routers/auth_router.py, backend/app/routers/auth_admin_integrity.py, backend/app/routers/auth_register_integrity.py, backend/app/routers/auth_setup_integrity.py, backend/app/routers/integrity_overrides.py, backend/app/routers/channel_integrations.py, backend/app/routers/channel_integrity.py, backend/app/routers/channel_webhook_integrity.py, backend/app/routers/channel_monitoring.py, backend/app/routers/ai_intelligence.py, backend/app/routers/ai_business_integrity.py, backend/app/routers/ai_slug_integrity.py, backend/app/routers/ai_customer_search_integrity.py, backend/app/routers/ai_order_product_integrity.py, backend/app/routers/ai_candidate_product_integrity.py, backend/app/routers/profiles.py, backend/app/routers/sales_profiles.py, backend/app/routers/public.py, backend/app/routers/faq.py, backend/app/routers/photo_requests.py, backend/app/routers/websocket.py, backend/app/routers/forecasting.py, backend/app/routers/analytics.py, backend/app/routers/super_admin_integrity.py, backend/app/routers/super_admin_audit_integrity.py, backend/app/middleware/business_integrity.py, backend/app/middleware/production_guards.py, backend/app/middleware/request_context.py, backend/app/dependencies/rate_limiting.py, backend/app/services/openai_service.py, backend/app/services/forecasting_service.py, backend/app/services/ai_intelligence_helpers.py, backend/app/utils/auth_security.py, backend/app/utils/location_access.py, backend/app/utils/sales_profile_config.py, backend/app/utils/s3_storage.py, backend/app/utils/websocket_manager.py, backend/app/utils/ai_sales_policy.py, backend/app/utils/photo_detection.py, backend/app/utils/rate_limiter.py, backend/app/models/ai.py, backend/app/models/photos.py, backend/app/models/rbac.py, backend/app/models/location.py, backend/app/schemas/ai.py, backend/app/schemas/photos.py, backend/app/schemas/auth.py, backend/app/schemas/rbac.py, backend/app/schemas/analytics.py, backend/app/jobs/forecasting_job.py, backend/app/ai_context_search.py, docs/n8n/whatsapp_ai_flow.json, docs/INTEGRACION_N8N.md, docs/AI_REPORTING_SCOPE.md

Lecturas parciales: backend/app/routers/super_admin.py (lectura extensa, salida combinada truncada; revisados endpoints principales y cancel transferencia), backend/app/services/order_service.py:159-245, backend/app/models/analytics.py, backend/tests/test_ai_workflow.py, backend/tests/test_photo_requests_flow.py, backend/tests/test_channel_integrations.py, backend/tests/test_channel_webhook_delivery_integrity.py, backend/tests/test_reports_analytics.py

No revisado/verificado: Código restante OrderService/stock/service validación delegada al auditor inventario, utils audit, logging/Sentry completas, Esquemas perfil/FAQ restantes y migrations referenciales completas, Integración n8n efectiva/Meta/perfiles/credenciales producción, PostgreSQL/CI/E2E/runtime/dependencias vulnerabilidades externas

## Limitaciones

Sin tests ejecutados por instrucción; sin importar app para evitar conexiones S3/startup.

Sin acceso ni llamadas a OpenAI, Meta, n8n, DB ni producción.

Evidencia de defectos estática, no frecuencia/incidentes de producción.

No se modificó repo, git ni servicios. Artefactos en /tmp para consolidación padre.

Mapa del auditor padre /tmp/softmobile-active-routes.json confirma rutas canónicas context/handle-message, legacy create-order/forecasting activo y webhook integrity. No ejecución propia app.

Auditor padre informa producción ENABLE_AI_FEATURES=false; SEC-AI-001/002/003 y CH001 camino API IA requieren habilitar IA. No inferir explotación producción.