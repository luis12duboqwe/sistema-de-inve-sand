# Auditoría UI, utilidades y documentación

SHA: `dba6763391d12c6c91c9904cba36725710f9280a`

Estado: lectura completa de 46 UI, 42 scripts/configs/typings, 32 documentos más AGENTS. package-lock parcial. 16 documentos pendientes. Repositorio sin modificaciones.

## Hallazgos

### UTIL-01 — HIGH — Arranque Windows resembra PostgreSQL y puede sobrescribir stock existente

Estado: confirmed_static

Referencias: `start-backend.bat:38-42`, `backend/init_db.py:20-27,80-83`, `backend/app/utils/demo_seed.py:293-329`, `backend/app/config.py:33-35`

El BAT decide inicializar por ausencia de inventory.db, independiente de DATABASE_URL. En PostgreSQL ese archivo normalmente no existe; init_db --with-data opera en engine configurado y _sync_stock actualiza cantidades existentes a valores demo sin StockHistory en rama update. No ejecutado.

Acción: Separar creación esquema de seeding; nunca sembrar en launcher; datos demo solo operación explícita sobre entorno aislado.

### UTIL-02 — HIGH — cleanup_v2 elimina documentación canónica

Estado: confirmed_static

Referencias: `cleanup_v2.sh:32-34,39-48,97-101`

Incluye COMIENZA_AQUI.md (existente y requerido por AGENTS) en FILES_TO_DELETE; mv sin -n puede sobrescribir docs/ARQUITECTURA.md si existe fuente histórica. CWD sin anclaje. No ejecutado.

Acción: Retirar utilidades destructivas legacy o convertirlas a plan/dry-run explícito con backup y lista validada.

### UTIL-03 — MEDIUM — Calendar pierde botones accesibles para navegar meses

Estado: confirmed_render

Referencias: `src/components/ui/calendar.tsx:61-67`, `node_modules/react-day-picker/dist/cjs/components/Nav.js`, `src/components/AdvancedSearchDialog.tsx:104-110`

DayPicker9 espera PreviousMonthButton/NextMonthButton interactivos; wrapper devuelve svg. SSR produce nav con dos SVG type=button sin button/role/tabIndex. Navegación mouse mantiene onclick, pero Tab/Enter/Space nativos faltan; SVG incluye Chevron hijo redundante.

Acción: Mantener botones de DayPicker y personalizar Chevron, actualizar classNames al API v9. Verificar rango y navegación teclado.

### UTIL-04 — LOW — Progress omite valor semántico ARIA

Estado: confirmed_render

Referencias: `src/components/ui/progress.tsx:6-25`

value se extrae y sólo modifica transform; no pasa a Root. SSR value65 da data-state indeterminate sin aria-valuenow. Consumido en SettingsDialog, OptimizationInsightsDialog, AIForecastingDialog.

Acción: Pasar value a Root y verificar ARIA 0/65/100.

### UTIL-05 — MEDIUM — test-system tolera tests frontend fallidos y concluye éxito

Estado: confirmed_static

Referencias: `test-system.sh:3-4,10`

npm run test:coverage || echo ... continúa; backend exitoso hace terminar script 0 y Todas las pruebas finalizaron.

Acción: Propagar estado no cero de todos gates; no tratar tests fallidos como ausencia de tests.

### UTIL-06 — MEDIUM — Quickstart canónico llama setup faltante

Estado: confirmed_static

Referencias: `start-all.sh:9-26`, `README.md:38-55`, `COMIENZA_AQUI.md:5-12`

Cuando no existe backend/venv o node_modules hace chmod/ejecución setup-complete.sh; archivo no existe en SHA. Sigue sin set-e y puede anunciar configuración/arranque exitosos. .venv permitido por otros launchers tampoco lo reconoce.

Acción: Alinear quickstart a instalación existente, crear venv explícitamente y usar launcher fail-fast con checks reales.

### UTIL-07 — MEDIUM — Simulaciones n8n no autentican discovery protegido y simulan éxito por prints

Estado: confirmed_static

Referencias: `test_n8n_simulation.py:21-36`, `simulate_whatsapp_flow.py:13-29`, `verify_learning.py:11-17`, `backend/app/routers/sales_profiles.py:61`

GET sales-profiles sin bearer ni _headers; endpoint exige check_any_permission. X-N8N-Token no sustituye JWT de discovery. Scripts retornan/capturan excepciones sin exit no cero; test_n8n_flow no tiene asserts y puede pasar pytest tras error. Algunos POST log no comprueban status y anuncian éxito.

Acción: Usar JWT de usuario fixture autorizado, service endpoints con token separado, timeout y raise/assert por cada resultado; aislar datos demo y cleanup.

### UTIL-08 — MEDIUM — Configurador PostgreSQL rompe credenciales con caracteres normales e interpola SQL privilegiado

Estado: confirmed_static

Referencias: `setup-postgres.sh:120-142,156,179`

Password con apóstrofe se inserta literalmente en CREATE USER PASSWORD; identificadores sin quoting/validación; operaciones psql ignoran PG_HOST/PG_PORT elegidos, conectan al postgres local. URL no percent-encode para @ / #, sed replacement no escapa &, |.

Acción: Usar quoting identificadores/literales psql, destino host/port único y URL con urllib quote; escribir dotenv sin sed interpolado.

### UTIL-09 — LOW — Root check_*.py auditan SQLite legacy y ocultan fallos

Estado: confirmed_static

Referencias: `check_db_direct.py:4-25`, `check_ai_tables.py:4-36`, `check_user_role.py:5-31`, `check_users_schema.py:6-36`, `inspect_last_order.py:4-8`

Rutas inventory.db fijas no DATABASE_URL; varios imprimen error pero código0. inspect_last_order abre connect sin comprobar existencia y crea archivo vacío. No validan PostgreSQL productivo.

Acción: Marcar compatibilidad SQLite, URI mode=ro y códigos de salida correctos; herramientas productivas deben usar engine config explícito y no exponer registros cliente.

### UTIL-10 — MEDIUM — reset_system anuncia reseteo aunque no aplica a PostgreSQL y mata uvicorn globalmente

Estado: confirmed_static

Referencias: `reset_system.sh:6-23`

pkill -f uvicorn mata todos procesos coincidentes del usuario; rm backend/inventory.db ignora DATABASE_URL y sin backup; init_db crea tablas sin vaciar PG existente. No set-e y siempre anuncia éxito. No ejecutado.

Acción: Retirar reset legacy del camino operativo; pruebas sólo DB aislada, PID concreto y confirmación/backup explícitos.

### UTIL-11 — LOW — Dialog y AlertDialog fuerzan pantalla completa también desktop

Estado: confirmed_static

Referencias: `src/components/ui/dialog.tsx:59-62`, `src/components/ui/alert-dialog.tsx:58-60`

!w-screen !h-[100dvh] !max-w-none !max-h-none son important y prevalecen sobre sm:w/height/max*. La intención responsive y max-width del caller no se aplica.

Acción: Limitar important al breakpoint móvil o quitarlo; comprobar contenido crítico desktop/mobile.

### UTIL-12 — LOW — ChartTooltipContent oculta valores cero

Estado: confirmed_static_unused

Referencias: `src/components/ui/chart.tsx:248-252`

Guard item.value && devuelve 0 desnudo en React, sin span ni formato previsto; cero se oculta o queda texto crudo. No consumidores de wrapper chart fuera UI encontrados; bug latente.

Acción: Comprobar != null y renderizar formato para 0.

### DOC-01 — MEDIUM — LIMITATIONS contradice conversión USD implementada

Estado: confirmed_static

Referencias: `docs/LIMITATIONS.md:5-15`, `docs/ARQUITECTURA.md:17`, `docs/PROMPT_NEGOCIACION_BOT.md:79-92`, `backend/app/utils/order_currency.py:15-59`, `backend/app/services/order_service.py:176`

LIMITATIONS afirma no conversión automática/moneda solo compatibilidad; helper convierte catálogo+costo USD a HNL con exchange_rate del perfil y fallback25; la guía negociación lo describe. Arquitectura HNL final es correcto pero compatibilidad-only es impreciso.

Acción: Documentar catálogo USD→ledger HNL, tasa utilizada y límites reales sobre historial y monedas soportadas.

### DOC-02 — MEDIUM — Guías de producción vigentes aparentes omiten gates y dan falsa preparación

Estado: confirmed_static

Referencias: `SETUP_PRODUCCION_RAPIDO.md:1-14,105-128,218`, `docs/PROD_INFRA_SECURITY.md:17-35,87-96`, `docs/DEPLOYMENT_PROD.md:42-49,94-105`, `setup-production.sh:203`

Guías antiguas no rotuladas histórico remiten a root setup manual/cron o compose sin perfiles backup/offsite y no gate validate-prod; afirman producción lista. Contradicen runbook canónico que exige offsite, DR, secretos fuertes, CI y reglas release.

Acción: Convertir cada guía histórica a redirect/banner canónico; scripts root producción deben delegar a deploy gate.

### DOC-03 — MEDIUM — Integración n8n tiene JSON corrupto y contratos obsoletos

Estado: confirmed_static

Referencias: `docs/INTEGRACION_N8N.md:23-37,66-99,146-159`, `docs/AI_REPORTING_SCOPE.md:13-28`, `TEST_N8N.md:25-35`

§3 JSON queda abierto y se mezcla con §4; sales_profile_id/query y message_source/platform vs scripts actuales slug/message_content/role/content; seguridad dice API pública y propone implementar auth pese RBAC existente. AI scope aún exige N8N y marca Prometheus futuro aunque runbook actual los soporta.

Acción: Reescribir usando schemas actuales y una prueba contractual fixture; autenticación exacta X-N8N-Token versus JWT.

## Verificación

13 root shell files bash -n exit0

14 root Python scripts ast.parse OK without executing imports

Vite SSR Calendar/Progress artifact /tmp/utilities-render-evidence.txt; optimizeDeps discovery disabled; exit0

git status --short remained empty

## Limitaciones

No destructive utility executed; no live DB/simulator operations

No browser E2E/Windows runtime performed

No exhaustive dependency lock audit

Chart SSR attempt inconclusive because ResponsiveContainer has no SSR size; zero finding based on exact conditional

Source snippets supporting currency/auth/seeding inspected only; full coverage credited to other agents if independently reviewed

## Cobertura exacta

- complete_read — `AGENTS.md` (165 líneas)

- complete_read — `src/components/ui/accordion.tsx` (64 líneas)

- complete_read — `src/components/ui/alert-dialog.tsx` (160 líneas)

- complete_read — `src/components/ui/alert.tsx` (66 líneas)

- complete_read — `src/components/ui/aspect-ratio.tsx` (10 líneas)

- complete_read — `src/components/ui/avatar.tsx` (53 líneas)

- complete_read — `src/components/ui/badge.tsx` (46 líneas)

- complete_read — `src/components/ui/breadcrumb.tsx` (110 líneas)

- complete_read — `src/components/ui/button.tsx` (59 líneas)

- complete_read — `src/components/ui/calendar.tsx` (74 líneas)

- complete_read — `src/components/ui/card.tsx` (92 líneas)

- complete_read — `src/components/ui/carousel.tsx` (242 líneas)

- complete_read — `src/components/ui/chart.tsx` (363 líneas)

- complete_read — `src/components/ui/checkbox.tsx` (32 líneas)

- complete_read — `src/components/ui/collapsible.tsx` (32 líneas)

- complete_read — `src/components/ui/command.tsx` (177 líneas)

- complete_read — `src/components/ui/context-menu.tsx` (254 líneas)

- complete_read — `src/components/ui/dialog.tsx` (139 líneas)

- complete_read — `src/components/ui/drawer.tsx` (130 líneas)

- complete_read — `src/components/ui/dropdown-menu.tsx` (259 líneas)

- complete_read — `src/components/ui/form.tsx` (165 líneas)

- complete_read — `src/components/ui/hover-card.tsx` (42 líneas)

- complete_read — `src/components/ui/input-otp.tsx` (77 líneas)

- complete_read — `src/components/ui/input.tsx` (25 líneas)

- complete_read — `src/components/ui/label.tsx` (24 líneas)

- complete_read — `src/components/ui/menubar.tsx` (276 líneas)

- complete_read — `src/components/ui/navigation-menu.tsx` (168 líneas)

- complete_read — `src/components/ui/pagination.tsx` (125 líneas)

- complete_read — `src/components/ui/popover.tsx` (48 líneas)

- complete_read — `src/components/ui/progress.tsx` (29 líneas)

- complete_read — `src/components/ui/radio-group.tsx` (45 líneas)

- complete_read — `src/components/ui/resizable.tsx` (54 líneas)

- complete_read — `src/components/ui/scroll-area.tsx` (58 líneas)

- complete_read — `src/components/ui/select.tsx` (185 líneas)

- complete_read — `src/components/ui/separator.tsx` (28 líneas)

- complete_read — `src/components/ui/sheet.tsx` (137 líneas)

- complete_read — `src/components/ui/sidebar.tsx` (726 líneas)

- complete_read — `src/components/ui/skeleton.tsx` (14 líneas)

- complete_read — `src/components/ui/slider.tsx` (63 líneas)

- complete_read — `src/components/ui/sonner.tsx` (21 líneas)

- complete_read — `src/components/ui/switch.tsx` (31 líneas)

- complete_read — `src/components/ui/table.tsx` (114 líneas)

- complete_read — `src/components/ui/tabs.tsx` (66 líneas)

- complete_read — `src/components/ui/textarea.tsx` (18 líneas)

- complete_read — `src/components/ui/toggle-group.tsx` (73 líneas)

- complete_read — `src/components/ui/toggle.tsx` (45 líneas)

- complete_read — `src/components/ui/tooltip.tsx` (59 líneas)

- complete_read — `TS_FIX.py` (34 líneas)

- complete_read — `api-examples-nuevo-sistema.json` (447 líneas)

- complete_read — `browser_cleanup_script.js` (23 líneas)

- complete_read — `check-production-setup.sh` (275 líneas)

- complete_read — `check_ai_tables.py` (36 líneas)

- complete_read — `check_db_direct.py` (25 líneas)

- complete_read — `check_luhn.py` (33 líneas)

- complete_read — `check_roles.py` (29 líneas)

- complete_read — `check_user_role.py` (33 líneas)

- complete_read — `check_users_schema.py` (39 líneas)

- complete_read — `cleanup.sh` (77 líneas)

- complete_read — `cleanup_system.py` (155 líneas)

- complete_read — `cleanup_v2.sh` (105 líneas)

- complete_read — `components.json` (21 líneas)

- complete_read — `eslint.config.js` (33 líneas)

- complete_read — `inspect_last_order.py` (74 líneas)

- complete_read — `package.json` (121 líneas)

- complete_read — `playwright.config.ts` (16 líneas)

- complete_read — `reset_system.sh` (33 líneas)

- complete_read — `runtime.config.json` (3 líneas)

- complete_read — `setup-postgres.sh` (255 líneas)

- complete_read — `setup-production.sh` (205 líneas)

- complete_read — `setup-sentry.sh` (273 líneas)

- complete_read — `simple_tsc.py` (34 líneas)

- complete_read — `simulate_whatsapp_flow.py` (96 líneas)

- complete_read — `spark.meta.json` (4 líneas)

- complete_read — `start-all-postgres.sh` (133 líneas)

- complete_read — `start-all.sh` (128 líneas)

- complete_read — `start-backend-codespaces.sh` (59 líneas)

- complete_read — `start-backend.bat` (60 líneas)

- complete_read — `start-backend.sh` (76 líneas)

- complete_read — `start-frontend.bat` (54 líneas)

- complete_read — `start-frontend.sh` (72 líneas)

- complete_read — `tailwind.config.js` (142 líneas)

- complete_read — `test-system.sh` (10 líneas)

- complete_read — `test_luhn.py` (339 líneas)

- complete_read — `test_n8n_simulation.py` (224 líneas)

- complete_read — `theme.json` (1 líneas)

- complete_read — `tsconfig.json` (38 líneas)

- complete_read — `verify_learning.py` (45 líneas)

- complete_read — `vite.config.ts` (92 líneas)

- complete_read — `src/vite-end.d.ts` (32 líneas)

- complete_read — `README.md` (136 líneas)

- complete_read — `COMIENZA_AQUI.md` (82 líneas)

- complete_read — `CHECKLIST_PRODUCCION.md` (96 líneas)

- complete_read — `DEPLOY_CHECKLIST.md` (99 líneas)

- complete_read — `docs/LIMITATIONS.md` (81 líneas)

- complete_read — `docs/AI_REPORTING_SCOPE.md` (84 líneas)

- complete_read — `docs/PRODUCCION_FINAL.md` (242 líneas)

- complete_read — `docs/ARQUITECTURA.md` (480 líneas)

- complete_read — `docs/OPERACION.md` (57 líneas)

- complete_read — `docs/DEPENDENCY_MAINTENANCE.md` (15 líneas)

- complete_read — `docs/PREPRODUCTION_MAINTENANCE_PLAN.md` (39 líneas)

- complete_read — `docs/PRODUCCION_COMPLETA.md` (46 líneas)

- complete_read — `docs/PROD_INFRA_SECURITY.md` (96 líneas)

- complete_read — `docs/SYNC_STRATEGY.md` (62 líneas)

- complete_read — `SECURITY.md` (25 líneas)

- complete_read — `PHOTO_REQUESTS_TODOS.md` (37 líneas)

- complete_read — `docs/CONVENCION_NOMBRES.md` (84 líneas)

- complete_read — `docs/EXECUCION_PARALELA_PLAN.md` (74 líneas)

- complete_read — `docs/REFACTORING_STATUS.md` (66 líneas)

- complete_read — `docs/RBAC_REFACTOR_PLAN.md` (69 líneas)

- complete_read — `docs/SEGURIDAD.md` (33 líneas)

- complete_read — `docs/VALIDATION_PLAN.md` (81 líneas)

- complete_read — `INICIO_RAPIDO.md` (247 líneas)

- complete_read — `SETUP_PRODUCCION_RAPIDO.md` (227 líneas)

- complete_read — `TEST_N8N.md` (98 líneas)

- complete_read — `AUDIT_SUMMARY.md` (62 líneas)

- complete_read — `AUDIT_REPORT.md` (158 líneas)

- complete_read — `docs/ACTUALIZAR_INSTALACION_EXISTENTE.md` (170 líneas)

- complete_read — `docs/DEPLOYMENT_PROD.md` (105 líneas)

- complete_read — `docs/DIAGNOSTICO_MODELO_VENTAS.md` (143 líneas)

- complete_read — `docs/INTEGRACION_N8N.md` (159 líneas)

- complete_read — `docs/PROMPT_NEGOCIACION_BOT.md` (141 líneas)

- partial — `package-lock.json` (9993 líneas)

- not_reviewed — `CHANGELOG_AI_IMPROVEMENTS_V2.md` (210 líneas)

- not_reviewed — `CHANNELS_CONFIGURATION.md` (529 líneas)

- not_reviewed — `PHOTO_REQUESTS_SYSTEM.md` (488 líneas)

- not_reviewed — `PRODUCTION_IMPROVEMENTS.md` (490 líneas)

- not_reviewed — `docs/DEPLOYMENT.md` (494 líneas)

- not_reviewed — `docs/ESTADO_IA.md` (380 líneas)

- not_reviewed — `docs/GUIA_REFACTORIZACION.md` (754 líneas)

- not_reviewed — `docs/GUIA_TESTING.md` (326 líneas)

- not_reviewed — `docs/GUIA_TRANSFERENCIAS.md` (259 líneas)

- not_reviewed — `docs/INTEGRACION.md` (211 líneas)

- not_reviewed — `docs/MANUAL_COMPLETO.md` (466 líneas)

- not_reviewed — `docs/PRD.md` (274 líneas)

- not_reviewed — `docs/RESUMEN_MEJORAS.md` (609 líneas)

- not_reviewed — `docs/TESTING_PLAN.md` (511 líneas)

- not_reviewed — `docs/TESTING_RESULTS.md` (371 líneas)

- not_reviewed — `docs/VALIDACION.md` (302 líneas)
