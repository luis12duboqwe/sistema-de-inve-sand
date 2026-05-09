# Alcance Final de IA, Reportes y Monitoreo

## Resumen Ejecutivo
- **Objetivo**: Congelar el alcance de las capacidades de IA, reportes analiticos y monitoreo operativo para el release v2.0 del *Sistema de Inventario Multi-Ubicacion*.
- **Principios**: Priorizar funcionalidades ya implementadas en backend (`backend/app/routers/ai_intelligence.py`, `backend/app/routers/reports.py`) y componentes comprobados en frontend (`src/hooks/use-forecasting.ts`, `src/hooks/use-health-check.ts`). Marcar como *BETA* o *Fase 2* cualquier pieza que dependa de OpenAI avanzada o jobs asincronos.
- **Resultado**: Este documento funciona como contrato de alcance. Todo lo que este "Incluido" debe probarse y documentarse; lo marcado como "Fuera de Alcance" alimenta el backlog de la siguiente fase.
- **Decisión v2.0 (2026-01-03)**: Las capacidades de IA se liberan en modo **BETA con heurísticas locales** y, opcionalmente, OpenAI. Toda la ruta `/api/ai/*` queda detrás del flag `ENABLE_AI_FEATURES`; si el flag está en `false`, los endpoints responden `503` para evitar falsas expectativas en entornos sin N8N/OpenAI.

## Tabla de Alcance v2.0

| Pilar | Estado v2.0 | Incluye | Fuera de alcance inmediato | Responsable |
| --- | --- | --- | --- | --- |
| Bots conversacionales | 75% (backend completo, integracion pendiente) | Endpoints `POST /api/ai/context`, `POST /api/ai/log-interaction`, `GET/POST /api/ai/config/{sales_profile_id}`, `GET /api/ai/status`; workflow N8N minimo para WhatsApp; metricas agregadas por permiso `reports:view`. | UI de chat en frontend, analisis multimodal (GPT-4 Vision), automatizacion de follow-ups. | Equipo IA + Integraciones (N8N).
| Pronosticos | 30% (MVP) | Hook `use-forecasting` etiquetado como BETA; consumo de `/api/ai/status` y `forecasting_service` para alertas; documentacion de limitaciones. | Modelos Prophet/ARIMA, jobs programados, cache en Redis. | Equipo Data.
| Insights de negocio | 60% (backend heurísticas + caché) | `use-optimization-insights.ts` consume `POST /api/ai/business-insights` (KPIs reales, almacenamiento en caché, fallback heurístico/AI opcional). | Llamadas avanzadas GPT-4, personalización por perfil, recomendaciones dinámicas multi-sucursal. | Equipo Producto/IA.
| Reportes operativos | 90% | APIs `/api/reports/*`, KPIs de dashboard, alertas de inventario, resumenes por ubicacion, permiso `reports:view`; documentacion de filtros/limitaciones. | Builder de reportes custom, exportaciones automaticas (PDF/Excel), scheduler de reportes. | Equipo Backend.
| Monitoreo | 60% | Endpoint `GET /api/ai/status`, hook `useHealthCheck`, script `simulate_whatsapp_flow.py` para smoke tests, alertas basicas via N8N. | Integracion con Prometheus/Grafana, tracing distribuido, SLA automatizados. | Equipo DevOps.

## 1. Inteligencia Artificial

### 1.1 Bots conversacionales
- **Backend listo**: Los endpoints en `backend/app/routers/ai_intelligence.py` cubren contexto, logging, training queue y configuracion por `SalesProfile`. `GET /api/ai/status` expone metricas globales y requiere `reports:view`.
- **Gating operacional**: El middleware interno `Depends(_ensure_ai_features_enabled)` devuelve `503` cuando `ENABLE_AI_FEATURES=false`, por lo que QA/DevOps deben dejar el flag en `true` solo cuando N8N + OpenAI estén configurados.
- **Integracion minima**: Mantener un workflow N8N (ver `docs/INTEGRACION_N8N.md`) con los pasos obligatorios: recibir mensaje -> `POST /api/ai/context` -> OpenAI API -> `POST /api/ai/log-interaction` -> responder cliente. Sin N8N no se considera GA.
- **Configuracion**: Variables `OPENAI_API_KEY`, `OPENAI_MODEL`, `N8N_WEBHOOK_URL` y `ENABLE_AI_FEATURES`. Si `ENABLE_AI_FEATURES=false` se debe retornar 503 en `/api/ai/*` (middleware sugerido en `docs/ESTADO_IA.md`).
- **Entrega v2.0**: Documentar el workflow, validar con `simulate_whatsapp_flow.py` y monitorear con `GET /api/ai/status`. Cualquier UI de chat queda explicitamente en backlog.

### 1.2 Pronosticos y alertas anticipadas
- **MVP**: `src/hooks/use-forecasting.ts` realiza regresion lineal local; debe mostrarse con badge *BETA* y limitarse a productos con >30 dias de historial.
- **Backend fortalecido**: `app/services/forecasting_service.py` ahora admite filtros por ubicacion/producto y se expone via `POST /api/analytics/forecast` (cacheable) y `GET /api/forecasting/predict` (lectura rapida).
- **Automatizacion**: Job diario con APScheduler (`ENABLE_FORECAST_SCHEDULER=true`) precalcula el snapshot para dashboards y N8N. Resultados se almacenan en `app.state.forecast_cache`.

### 1.3 Insights de negocio
- **Estado actual**: `use-optimization-insights.ts` llama `POST /api/ai/business-insights` para obtener KPIs reales, recomendaciones IA/fallback y respeta `use_cache` + `force_refresh`. TTL configurable (`BUSINESS_INSIGHTS_CACHE_SECONDS`).
- **Spec futuro**: Profundizar análisis (GPT-4 avanzado, personalización por perfil, insights multicanal) manteniendo backward compatibility del endpoint.
- **Monitoreo**: Registrar hits del endpoint en `GET /api/ai/status` y exponer `X-AI-Business-Cache` para dashboards de observabilidad.

### 1.4 Trade-in asistido
- **Alcance**: Solo flujo manual (`PendingTradeInsDialog.tsx` + `TradeInPolicy`). La asistencia con IA/vision se considera Fase 3 y debe comunicarse como exploratoria.

## 2. Reportes Analiticos

### 2.1 KPIs y reportes disponibles
- **Dashboard**: `/api/reports/dashboard` retorna KPIs globales/mensuales, margen bruto y ticket promedio. Respeta filtros `sales_profile_slug` y `location_id`.
- **Ventas**: `/api/reports/sales` entrega revenue, AOV y Top N productos en un rango; excluye ordenes canceladas.
- **Alertas de Inventario**: `/api/reports/inventory/alerts` clasifica `out_of_stock`, `critical`, `low`, con permiso `inventory:view`.
- **Ubicaciones**: `/api/reports/stock-summary-by-location` y `/api/reports/sales-summary-by-location` agregan inventario y ventas usando `Location` + `Order.source_location_id`.

### 2.2 Lineamientos de uso
- Todos los endpoints quedan detras de `check_permission("reports:view")` excepto alertas de inventario (usa `inventory:view`).
- Documentar en `README.md` como consultar filtros y ejemplos (seccion "Reportes") y enlazar `api-examples-nuevo-sistema.json`.
- Se sugiere construir dashboards en frontend (Radix cards) consumiendo estos endpoints; no se incluye un builder ni exportador automatico.

## 3. Monitoreo Operativo

### 3.1 Salud de la aplicacion
- **Hook `useHealthCheck`** (`src/hooks/use-health-check.ts`) sera la herramienta oficial dentro del frontend para detectar inconsistencias de productos/ordenes/perfiles. Debe exponer boton "Diagnosticar" y mostrar resultados/auto-fix.
- **API Status**: `GET /api/ai/status` funciona como endpoint de observabilidad ligera (tokens, backlog, alertas de forecast). Debe integrarse en panel interno o N8N para alertas.
- **Jobs manuales**: `simulate_whatsapp_flow.py` se ejecuta en CI/nigthly para smoke-test de bots.

### 3.2 Observabilidad y alertas
- **Logs**: Centralizar los eventos criticos (errores de IA, fallos de reportes) via logging estandar de FastAPI. Prioridad para centralizacion en DataDog/ELK en Fase 2.
- **Alertas N8N**: Configurar nodos que llamen `GET /api/ai/status` cada 5 min; disparar alerta si `training_backlog > 20`, `forecasting_alerts` no vacio por >24h, o si no hay interacciones en 6h (pico horarios).
- **Health endpoints**: `GET /api/health` está disponible en `backend/app/main.py` para monitoreo de uptime.

### 3.3 Feature Flags y permisos
- `ENABLE_AI_FEATURES` controla exposicion de `/api/ai/*`.
- Permisos minimos: `reports:view` para dashboards, `inventory:view` para alertas, `users:manage` para administracion RBAC.
- Para monitoreo programado se recomienda usar un token de servicio con solo `reports:view`.

## 4. Roadmap Posterior

1. **IA Completa (Fase 2)**
   - Implementar `POST /api/ai/business-insights` con GPT-4.
   - Anadir job programado y cache para pronosticos avanzados.
   - Explorar GPT-4 Vision para trade-in.
2. **Reporting Avanzado**
   - Constructor de reportes custom y exportaciones PDF/Excel.
   - Scheduler de reportes por correo/WhatsApp.
3. **Monitoreo Enterprise**
   - Integrar metricas en Prometheus/Grafana o Azure Monitor.
   - Anadir tracing (OpenTelemetry) y SLIs/SLOs publicos.

> **Nota**: Cualquier cambio de alcance debe versionar este archivo y actualizar `docs/ESTADO_IA.md` y `api-examples-nuevo-sistema.json` para mantener paridad entre documentacion y producto.
