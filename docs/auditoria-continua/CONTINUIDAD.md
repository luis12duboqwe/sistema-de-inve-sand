# Punto exacto de continuación

Fase: AUDITORÍA INCOMPLETA. Prohibido corregir/fusionar/desplegar.

Línea base main `dba6763391d12c6c91c9904cba36725710f9280a`; documentación en PR146, rama audit/channel-integrations-findings-20261014.

La revisión paralela alcanzó límite de uso durante ampliación; solo se incorporan lecturas guardadas explícitamente, no inferidas de mensajes ni trabajo interrumpido. La instalación de Chromium falló; PostgreSQL local no disponible. Los tests CI del SHA son evidencia válida, no sustituyen casos nuevos ni browser real. No queda auditoría autónoma programada tras cerrar turno.

Para retomar: leer README, COBERTURA.json, HALLAZGOS.json y VERIFICACIONES.md de este PR. Recuperar main/PRs y comparar blobs; conservar FULL_TEXT_REVIEWED si blob idéntico. Auditar listas siguientes sin repetir archivos completos. Prioridad: servicios frontend parciales (inventoryServiceFactory/inventoryService), componentes restantes; tests backend pendientes; utilitarios backend y docs pendientes. Luego reconciliar contratos/rutas efectivas y reproducir fallos sobre PostgreSQL16 descartable.

## Archivos que requieren continuación

- `.dockerignore` — NOT_REVIEWED
- `.github/copilot-instructions.md` — NOT_REVIEWED
- `.gitignore` — NOT_REVIEWED
- `.spark-initial-sha` — NOT_REVIEWED
- `CHANGELOG_AI_IMPROVEMENTS_V2.md` — NOT_REVIEWED
- `CHANNELS_CONFIGURATION.md` — NOT_REVIEWED
- `LICENSE` — NOT_REVIEWED
- `PHOTO_REQUESTS_SYSTEM.md` — NOT_REVIEWED
- `PRODUCTION_IMPROVEMENTS.md` — NOT_REVIEWED
- `backend/.dockerignore` — NOT_REVIEWED
- `backend/.env.example` — NOT_REVIEWED
- `backend/.env.example.channels` — NOT_REVIEWED
- `backend/.env.production.example` — NOT_REVIEWED
- `backend/.gitignore` — NOT_REVIEWED
- `backend/api-examples.json` — NOT_REVIEWED
- `backend/app/__init__.py` — NOT_REVIEWED
- `backend/app/channel_audit.py` — NOT_REVIEWED
- `backend/app/location_identity.py` — NOT_REVIEWED
- `backend/app/models/__init__.py` — NOT_REVIEWED
- `backend/app/models/analytics.py` — PARTIAL_REVIEWED
- `backend/app/models/system.py` — NOT_REVIEWED
- `backend/app/routers/__init__.py` — NOT_REVIEWED
- `backend/app/routers/super_admin.py` — PARTIAL_REVIEWED
- `backend/app/sales_profile_identity.py` — NOT_REVIEWED
- `backend/app/sales_profile_lookup.py` — NOT_REVIEWED
- `backend/app/schemas/__init__.py` — NOT_REVIEWED
- `backend/app/schemas/common.py` — NOT_REVIEWED
- `backend/app/schemas/faq.py` — NOT_REVIEWED
- `backend/app/schemas/location.py` — NOT_REVIEWED
- `backend/app/schemas/public.py` — NOT_REVIEWED
- `backend/app/schemas/stock_history.py` — NOT_REVIEWED
- `backend/app/services/__init__.py` — NOT_REVIEWED
- `backend/app/supplier_identity.py` — NOT_REVIEWED
- `backend/app/utils/README.md` — NOT_REVIEWED
- `backend/app/utils/__init__.py` — NOT_REVIEWED
- `backend/app/utils/agent_notifications.py` — NOT_REVIEWED
- `backend/app/utils/audit.py` — NOT_REVIEWED
- `backend/app/utils/bank_names.py` — NOT_REVIEWED
- `backend/app/utils/daily_close_code.py` — NOT_REVIEWED
- `backend/app/utils/demo_seed.py` — NOT_REVIEWED
- `backend/app/utils/html_export.py` — NOT_REVIEWED
- `backend/app/utils/logging_config.py` — NOT_REVIEWED
- `backend/app/utils/observability.py` — NOT_REVIEWED
- `backend/app/utils/prometheus_metrics.py` — NOT_REVIEWED
- `backend/app/utils/retry.py` — NOT_REVIEWED
- `backend/app/utils/runtime_metrics.py` — NOT_REVIEWED
- `backend/app/utils/sentry_config.py` — NOT_REVIEWED
- `backend/app/utils/supplier_names.py` — NOT_REVIEWED
- `backend/app/utils/validators.py` — NOT_REVIEWED
- `backend/test_forecasting.ipynb` — NOT_REVIEWED
- `backend/tests/__init__.py` — NOT_REVIEWED
- `backend/tests/test_ai_workflow.py` — PARTIAL_REVIEWED
- `backend/tests/test_api_flow.py` — NOT_REVIEWED
- `backend/tests/test_channel_integrations.py` — PARTIAL_REVIEWED
- `backend/tests/test_channel_webhook_delivery_integrity.py` — PARTIAL_REVIEWED
- `backend/tests/test_final_integrity_regressions.py` — NOT_REVIEWED
- `backend/tests/test_imei_admin_integrity.py` — NOT_REVIEWED
- `backend/tests/test_location_name_concurrency_integrity.py` — NOT_REVIEWED
- `backend/tests/test_multistore_ops_integrity.py` — NOT_REVIEWED
- `backend/tests/test_order_edit_pricing_integration.py` — NOT_REVIEWED
- `backend/tests/test_order_edit_term_preservation.py` — NOT_REVIEWED
- `backend/tests/test_order_pricing_policy.py` — NOT_REVIEWED
- `backend/tests/test_order_service_pricing_integration.py` — NOT_REVIEWED
- `backend/tests/test_photo_requests_flow.py` — PARTIAL_REVIEWED
- `backend/tests/test_pricing_policy_migration.py` — PARTIAL_REVIEWED
- `backend/tests/test_purchase_restock_lock_order_integrity.py` — NOT_REVIEWED
- `backend/tests/test_restock_inventory_count_lock_compatibility.py` — NOT_REVIEWED
- `backend/tests/test_restock_transfer_confirmation_lock_compatibility.py` — NOT_REVIEWED
- `backend/tests/test_sales_profile_router_guards.py` — NOT_REVIEWED
- `backend/tests/test_sales_profile_slug_concurrency_integrity.py` — NOT_REVIEWED
- `backend/tests/test_stock_history_access_stats.py` — NOT_REVIEWED
- `backend/tests/test_stock_manager_invariants.py` — NOT_REVIEWED
- `backend/tests/test_super_admin_audit_filters.py` — NOT_REVIEWED
- `backend/tests/test_super_admin_identity_concurrency.py` — NOT_REVIEWED
- `backend/tests/test_super_admin_product_purge.py` — NOT_REVIEWED
- `backend/tests/test_supplier_name_concurrency_integrity.py` — NOT_REVIEWED
- `backend/tests/test_transfer_creation_release_lock_compatibility.py` — NOT_REVIEWED
- `backend/tests/test_upgrade_audit.py` — PARTIAL_REVIEWED
- `backend/tests/test_websocket_manager.py` — NOT_REVIEWED
- `docs/DEPLOYMENT.md` — NOT_REVIEWED
- `docs/ESTADO_IA.md` — NOT_REVIEWED
- `docs/GUIA_REFACTORIZACION.md` — NOT_REVIEWED
- `docs/GUIA_TESTING.md` — NOT_REVIEWED
- `docs/GUIA_TRANSFERENCIAS.md` — NOT_REVIEWED
- `docs/INTEGRACION.md` — NOT_REVIEWED
- `docs/MANUAL_COMPLETO.md` — NOT_REVIEWED
- `docs/PRD.md` — NOT_REVIEWED
- `docs/RESUMEN_MEJORAS.md` — NOT_REVIEWED
- `docs/TESTING_PLAN.md` — NOT_REVIEWED
- `docs/TESTING_RESULTS.md` — NOT_REVIEWED
- `docs/VALIDACION.md` — NOT_REVIEWED
- `index.html` — NOT_REVIEWED
- `package-lock.json` — PARTIAL_REVIEWED
- `src/ErrorFallback.tsx` — NOT_REVIEWED
- `src/components/AIForecastingDialog.tsx` — NOT_REVIEWED
- `src/components/AIProfileConfigDialog.tsx` — NOT_REVIEWED
- `src/components/AIStatusDialog.tsx` — NOT_REVIEWED
- `src/components/AIStatusWidget.tsx` — NOT_REVIEWED
- `src/components/AITrainingCenter.tsx` — NOT_REVIEWED
- `src/components/AdvancedSearchDialog.tsx` — NOT_REVIEWED
- `src/components/BackendConnectionCheck.tsx` — NOT_REVIEWED
- `src/components/ChannelHealthDialog.tsx` — NOT_REVIEWED
- `src/components/CustomerHistoryDialog.tsx` — NOT_REVIEWED
- `src/components/CustomerInsights.tsx` — NOT_REVIEWED
- `src/components/CustomizeShortcutsDialog.tsx` — NOT_REVIEWED
- `src/components/DailyCloseDialog.tsx` — NOT_REVIEWED
- `src/components/DashboardStats.tsx` — NOT_REVIEWED
- `src/components/EditProductDialog.tsx` — NOT_REVIEWED
- `src/components/EditProfileDialog.tsx` — NOT_REVIEWED
- `src/components/FinancingSettings.tsx` — NOT_REVIEWED
- `src/components/ForecastingWidget.tsx` — NOT_REVIEWED
- `src/components/IMEIHistoryDialog.tsx` — NOT_REVIEWED
- `src/components/IMEIListDialog.tsx` — NOT_REVIEWED
- `src/components/ImportProductsDialog.tsx` — NOT_REVIEWED
- `src/components/KeyboardShortcutsDialog.tsx` — NOT_REVIEWED
- `src/components/LocationsList.tsx` — NOT_REVIEWED
- `src/components/LowStockAlert.tsx` — NOT_REVIEWED
- `src/components/LowStockReportDialog.tsx` — NOT_REVIEWED
- `src/components/ManageFAQsDialog.tsx` — NOT_REVIEWED
- `src/components/ManageSuppliersDialog.tsx` — NOT_REVIEWED
- `src/components/ManageUsersDialog.tsx` — NOT_REVIEWED
- `src/components/MultiStoreControlDialog.tsx` — NOT_REVIEWED
- `src/components/NewProductDialog.tsx` — NOT_REVIEWED
- `src/components/NewProfileDialog.tsx` — NOT_REVIEWED
- `src/components/NotificationSettingsDialog.tsx` — NOT_REVIEWED
- `src/components/OptimizationInsightsDialog.tsx` — NOT_REVIEWED
- `src/components/PendingTradeInsDialog.tsx` — NOT_REVIEWED
- `src/components/PendingTransfersDialog.tsx` — NOT_REVIEWED
- `src/components/PrintLabelsDialog.tsx` — NOT_REVIEWED
- `src/components/ProductCard.tsx` — NOT_REVIEWED
- `src/components/ProductIMEIRegistryDialog.tsx` — NOT_REVIEWED
- `src/components/ProductLabel.tsx` — NOT_REVIEWED
- `src/components/ProfileCard.tsx` — NOT_REVIEWED
- `src/components/ProfileConfigPrompt.tsx` — NOT_REVIEWED
- `src/components/ProfileDetailsDialog.tsx` — NOT_REVIEWED
- `src/components/ProfileSettingsDialog.tsx` — NOT_REVIEWED
- `src/components/ProfileSettingsSummary.tsx` — NOT_REVIEWED
- `src/components/ProfileSetupGuide.tsx` — NOT_REVIEWED
- `src/components/ProfilesConfigSummary.tsx` — NOT_REVIEWED
- `src/components/PublicCatalog.tsx` — NOT_REVIEWED
- `src/components/ReportsDialog.tsx` — NOT_REVIEWED
- `src/components/RestockProductDialog.tsx` — NOT_REVIEWED
- `src/components/ReturnsListDialog.tsx` — NOT_REVIEWED
- `src/components/SalesHistoryDialog.tsx` — NOT_REVIEWED
- `src/components/SalesProfilesList.tsx` — NOT_REVIEWED
- `src/components/SettingsDialog.tsx` — NOT_REVIEWED
- `src/components/StockByLocationDialog.tsx` — NOT_REVIEWED
- `src/components/StockHistoryDialog.tsx` — NOT_REVIEWED
- `src/components/StorageDiagnosticDialog.tsx` — NOT_REVIEWED
- `src/components/SuperAdminControlPanelDialog.tsx` — NOT_REVIEWED
- `src/components/SyncIndicator.tsx` — NOT_REVIEWED
- `src/components/SyncSettingsDialog.tsx` — NOT_REVIEWED
- `src/components/TradeInPoliciesDialog.tsx` — NOT_REVIEWED
- `src/components/ValidationCodeDialog.tsx` — NOT_REVIEWED
- `src/components/WarrantyCheckDialog.tsx` — NOT_REVIEWED
- `src/components/forms/RoleSelect.tsx` — NOT_REVIEWED
- `src/index.css` — NOT_REVIEWED
- `src/lib/aiForecasting.ts` — NOT_REVIEWED
- `src/lib/businessInsightsFallback.ts` — NOT_REVIEWED
- `src/lib/exportUtils.ts` — NOT_REVIEWED
- `src/lib/icon-proxies/lucide.ts` — NOT_REVIEWED
- `src/lib/icon-proxies/phosphor.ts` — NOT_REVIEWED
- `src/lib/importUtils.ts` — NOT_REVIEWED
- `src/lib/initialData.ts` — NOT_REVIEWED
- `src/lib/inventoryService.ts` — NOT_REVIEWED
- `src/lib/inventoryServiceFactory.ts` — PARTIAL_REVIEWED
- `src/lib/keyboardShortcuts.ts` — NOT_REVIEWED
- `src/lib/kvStorage.manual.ts` — NOT_REVIEWED
- `src/lib/labelPrint.ts` — NOT_REVIEWED
- `src/lib/optimizationAnalytics.ts` — NOT_REVIEWED
- `src/lib/pdfExport.ts` — NOT_REVIEWED
- `src/lib/reportUtils.ts` — NOT_REVIEWED
- `src/lib/syncJournal.ts` — NOT_REVIEWED
- `src/lib/syncService.ts` — NOT_REVIEWED
- `src/lib/types.ts` — PARTIAL_REVIEWED
- `src/main.css` — NOT_REVIEWED
- `src/main.tsx` — NOT_REVIEWED
- `src/styles/theme.css` — NOT_REVIEWED
- `src/test/msw/handlers.ts` — NOT_REVIEWED
- `src/test/msw/server.ts` — NOT_REVIEWED
- `typings/apscheduler/schedulers/asyncio/__init__.pyi` — NOT_REVIEWED
- `typings/apscheduler/triggers/cron/__init__.pyi` — NOT_REVIEWED

## Plan de corrección provisional (NO ejecutar)

1. Completar cobertura, revisar falsos positivos/duplicados y finalizar dictamen.
2. Con autorización: reservas venta/traslado, recepción0IMEI, garantías/retomas e idempotencia; regresiones PostgreSQL.
3. RBAC por ubicación y contratos pagos mixtos; conciliar ledger/totales.
4. Backups/restore/migraciones y deployment reproducible.
5. Mensajes/fotos/deduplicación y credenciales de integración en staging.
6. Frontend errores/paginación/cache, utilitarios legacy y documentos.
7. PRs mínimos por dependencia, CI más pruebas de regresión; staging operativo completo, DR y release gates reales; despliegue solo con autorización.
