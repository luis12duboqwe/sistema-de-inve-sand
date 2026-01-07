# Plan de Ejecución Paralela

## Objetivo
Despejar los siete frentes pendientes (inventario/concurrencia, validaciones UI, infraestructura productiva, consistencia/naming, RBAC UI, IA-reportes, monitoreo) sin bloquear el flujo actual. El plan divide responsabilidades por capa y fija entregables claros por iteración.

## Principios
- Mantener la rama `main` estable: cada frente trabaja en ramas cortas y PRs acotados.
- Compartir utilidades comunes (p.ej., helpers de stock, hooks de validación) para evitar duplicación.
- Documentar supuestos y resultados parciales en `docs/` al cerrar cada bloque.
- Automatizar verificaciones donde sea posible (tests de concurrencia, lint, scripts de deploy).

## Roadmap Paralelo

### 1. Inventario / Concurrencia (Backend)
- **Responsable:** Backend
- **Entregables:**
  - Suite `tests/test_stock_concurrency.py` con escenarios de órdenes simultáneas, transferencias cruzadas y reservas.
  - Refactor de `stock_transaction_helper.py` y `orders.py` para usar helpers como `validate_and_reserve_stock`, `calculate_order_totals`, `process_trade_in`.
- **Dependencias:** Base de datos con soporte a `SELECT ... FOR UPDATE` (SQLite en modo WAL temporalmente, luego PostgreSQL).
- **Estado 2026-01-02:** helper unificado para retomas/totales y suite `backend/tests/test_stock_concurrency.py` creada.

### 2. Validaciones y UX (Frontend)
- **Responsable:** Frontend
- **Entregables:**
  - Validaciones previas al submit en `StockTransferDialog`, `NewOrderDialog`, `TradeInDialogs`, `ImportProductsDialog`.
  - Pruebas de regresión (Vitest/Playwright) o al menos stories documentadas.
- **Dependencias:** Hooks de validación compartidos (`useFormGuard`), mensajes de error estandarizados en `lib/errors.ts`.
- **Estado 2026-01-02:** Formularios `NewOrderDialog`, `ImportProductsDialog`, `TradeInPoliciesDialog` y `PendingTradeInsDialog` consumen los esquemas de `src/lib/validation/*`, se añadieron mensajes inline y limpieza de errores; `StockTransferDialog` ya contaba con su guardado en Zod y se documentó la revisión.

### 3. Infraestructura y Seguridad
- **Responsable:** DevOps
- **Entregables:**
  - `docker-compose.prod.yml` con PostgreSQL + backend + frontend.
  - Guía `docs/DEPLOYMENT_PROD.md` explicando SECRET_KEY, CORS_ALLOW, rate limiting (middleware FastAPI) y headers de seguridad.
- **Dependencias:** Scripts existentes (`start-backend.sh`, `start-frontend.sh`).
- **Estado 2026-01-02:** Se añadió `deploy/docker-compose.prod.yml` (PostgreSQL + FastAPI + frontend Nginx) y las guías `docs/DEPLOYMENT_PROD.md` / `docs/PROD_INFRA_SECURITY.md`; se documentó el uso de `.env.prod`, healthchecks y el proxy TLS externo.

### 4. Consistencia / Modularización + RBAC UI
- **Responsable:** Backend + Frontend compartido
- **Entregables:**
  - Reorganización de `backend/app/models/` y `schemas/` en módulos por dominio.
  - Convención de naming publicada en `docs/CONVENCION_NOMBRES.md`.
  - Nueva pantalla `AdminUsersDialog` (o sección en `AdminPanel`) para gestionar usuarios/roles usando `auth_router`.
- **Dependencias:** Endpoints ya expuestos (`GET/PUT /users`).
- **Estado 2026-01-02:** `app.models` opera como paquete modular, `app.schemas` ahora es paquete con módulos dedicados (`rbac.py`, `location.py`, `product.py`), se añadió la guía `docs/CONVENCION_NOMBRES.md` y la consola `ManageUsersDialog` + `use-rbac` habilita CRUD de usuarios/roles cuando el modo API está activo.

### 5. IA / Forecasting / Reportes
- **Responsable:** AI Team
- **Entregables:**
  - Decisión documentada: integrar OpenAI (con claves y job scheduler) o marcar funcionalidad como beta.
  - Validación de KPIs (margen, ticket promedio) con dataset real; ajustar `ReportsDashboard` y `reports.py` según hallazgos.
  - Actualización del roadmap en `docs/ARQUITECTURA.md` y PRD.
- **Dependencias:** Datos históricos, posibles colas (RQ/Celery) si se implementa integración real.
- **Estado 2026-01-03:** IA se libera como BETA con heurísticas + OpenAI opcional, `/api/ai/*` queda detrás de `ENABLE_AI_FEATURES`, y la documentación (`docs/AI_REPORTING_SCOPE.md`, `docs/ESTADO_IA.md`) refleja la decisión y lineamientos de KPIs.

### 6. Monitoreo / Observabilidad
- **Responsable:** DevOps/Backend
- **Entregables:**
  - Configuración de logging estructurado (JSON) y almacenamiento (archivos rotativos o servicio externo).
  - Manejo homogéneo de errores (códigos controlados, sin stack trace expuesto) y documentación en `docs/OPERACION.md`.
  - Integración propuesta (APM ligero o herramientas como Sentry).
- **Dependencias:** Ajustes en `settings.py` y `main.py` para middlewares.
- **Estado 2026-01-03:** Logging configurable via `.env`, middleware de correlación `RequestContextMiddleware`, documentación en `docs/OPERACION.md` y bootstrap opcional de Sentry listos en `main.py`.

## Iteraciones Sugeridas
1. **Semana 1:** Backend concur. tests + refactor helpers, plan de naming, diseño UI RBAC.
2. **Semana 2:** Validaciones frontend + módulos de models/schemas + Docker prod stack.
3. **Semana 3:** IA/reportes (decisión final + implementación) + logging/APM + guía de despliegue.
4. **QA Final:** Pruebas E2E cubriendo importaciones, devoluciones, cancelaciones, exportaciones.

## Seguimiento
- Actualizar este documento al cerrar cada frente (fecha, PR, responsables).
- Usar Issues/Projects para rastrear sub-tareas.
- Reunión corta al inicio de cada semana para redistribuir carga según avance.
