# Cobertura verificable

Todos los 653 archivos rastreados de la línea base se incluyen conservadoramente: código, pruebas, scripts, configuración y documentación; sin exclusiones para inflar cobertura. No incluye documentos nuevos de auditoría. Lectura completa no implica corrección ni prueba runtime.

{'FULL_TEXT_REVIEWED': 552, 'NOT_REVIEWED': 93, 'PARTIAL_REVIEWED': 8}; lectura completa 84.53%.

| Archivo | Estado | Evidencia |
|---|---|---|
| .dockerignore | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| .github/copilot-instructions.md | NOT_REVIEWED |  |
| .github/dependabot.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| .github/workflows/browser-e2e.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| .github/workflows/ci.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| .github/workflows/dr-drill.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| .github/workflows/release-gate.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| .gitignore | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| .spark-initial-sha | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| AGENTS.md | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_deploy.json, BLOQUE_frontend.json, BLOQUE_tests.json, BLOQUE_utilities.json, Lectura íntegra del coordinador en esta ejecución |
| AUDIT_REPORT.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json, Lectura íntegra del coordinador en esta ejecución |
| AUDIT_SUMMARY.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json, Lectura íntegra del coordinador en esta ejecución |
| CHANGELOG_AI_IMPROVEMENTS_V2.md | NOT_REVIEWED | BLOQUE_utilities.json |
| CHANNELS_CONFIGURATION.md | NOT_REVIEWED | BLOQUE_utilities.json |
| CHECKLIST_PRODUCCION.md | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_utilities.json |
| COMIENZA_AQUI.md | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_utilities.json |
| DEPLOY_CHECKLIST.md | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_utilities.json |
| Dockerfile.frontend | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| INICIO_RAPIDO.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| LICENSE | NOT_REVIEWED |  |
| PHOTO_REQUESTS_SYSTEM.md | NOT_REVIEWED | BLOQUE_utilities.json |
| PHOTO_REQUESTS_TODOS.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| PRODUCTION_IMPROVEMENTS.md | NOT_REVIEWED | BLOQUE_utilities.json |
| README.md | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_utilities.json |
| SECURITY.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| SETUP_PRODUCCION_RAPIDO.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| TEST_N8N.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| TS_FIX.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| api-examples-nuevo-sistema.json | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| backend/.dockerignore | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/.env.example | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/.env.example.channels | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/.env.production.example | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/.gitignore | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/Dockerfile | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/QUICKSTART.md | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/README.md | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/api-examples.json | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/__init__.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/ai_context_search.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/auth.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/channel_audit.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/config.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_security-ai.json |
| backend/app/config_production.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_security-ai.json |
| backend/app/crypto.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/database.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_deploy.json |
| backend/app/dependencies/rate_limiting.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/jobs/forecasting_job.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/location_identity.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/main.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_deploy.json, BLOQUE_security-ai.json |
| backend/app/middleware/business_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_security-ai.json |
| backend/app/middleware/production_guards.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/middleware/request_context.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/models/__init__.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/models/ai.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/models/analytics.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json, CONTINUACION_02.json |
| backend/app/models/control.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/models/finance.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/models/location.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_security-ai.json |
| backend/app/models/order.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/models/photos.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/models/product.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/models/rbac.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/models/system.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/routers/__init__.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/routers/ai_business_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/ai_candidate_product_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/ai_customer_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/ai_intelligence.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/ai_order_product_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/ai_slug_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/analytics.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/auth_admin_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/auth_register_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/auth_router.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/auth_setup_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/channel_integrations.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/channel_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/channel_monitoring.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/channel_webhook_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/customers.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/daily_close.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_frontend.json |
| backend/app/routers/faq.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/financing.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/forecasting.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/imeis.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/integrity_overrides.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_security-ai.json |
| backend/app/routers/locations.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/multistore_control.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/multistore_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/multistore_ops_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/order_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/order_state_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/orders.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_frontend.json |
| backend/app/routers/photo_requests.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/product_imei_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/product_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/products.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/profiles.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/public.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/reports.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/reports_final_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/reports_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/return_serial_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/returns.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_frontend.json |
| backend/app/routers/sales_profiles.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/stock_history.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/stock_transfer_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/stock_transfers.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_frontend.json |
| backend/app/routers/super_admin.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json, CONTINUACION_02.json |
| backend/app/routers/super_admin_audit_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/super_admin_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/routers/suppliers.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/routers/websocket.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/sales_profile_identity.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/sales_profile_lookup.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/schemas/__init__.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/schemas/ai.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/schemas/analytics.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/schemas/auth.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/schemas/common.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/schemas/control.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/schemas/daily_close.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/schemas/faq.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/schemas/finance.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/schemas/imei.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/schemas/location.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/schemas/order.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_frontend.json |
| backend/app/schemas/order_secure.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/schemas/photos.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/schemas/product.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/schemas/public.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/schemas/rbac.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/schemas/returns.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/schemas/stock_history.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/services/__init__.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/services/ai_intelligence_helpers.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/services/forecasting_service.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/services/openai_service.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/services/order_service.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_frontend.json, BLOQUE_security-ai.json |
| backend/app/services/stock_transaction_helper.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/startup_schema_lock.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/app/supplier_identity.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/tests/test_locations.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/app/tests/test_multistore_control.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/app/tests/test_orders_validations.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/app/tests/test_stock_transactions.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/app/utils/README.md | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/__init__.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/agent_notifications.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/ai_sales_policy.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/utils/audit.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/auth_security.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/utils/auto_migrations.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/app/utils/bank_names.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/daily_close_code.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/demo_seed.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/html_export.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/location_access.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_security-ai.json |
| backend/app/utils/logging_config.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/observability.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/order_currency.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/utils/order_financing.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_frontend.json |
| backend/app/utils/order_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/utils/order_item_currency_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/utils/order_pricing.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/utils/order_queries.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/utils/order_tradeins.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/utils/order_validators.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/utils/photo_detection.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/utils/pricing_policy_migration.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/app/utils/prometheus_metrics.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/rate_limiter.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/utils/retry.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/runtime_metrics.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/s3_storage.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/utils/sales_profile_config.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/app/utils/sentry_config.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/stock_manager.py | FULL_TEXT_REVIEWED | BLOQUE_business.json |
| backend/app/utils/supplier_names.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/validators.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/app/utils/websocket_manager.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| backend/apply_migrations_direct.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/backup_database.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/check_channels_config.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/check_db.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/check_faqs.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/check_production_readiness.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/conftest.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_deploy.json, BLOQUE_tests.json, Lectura íntegra del coordinador en esta ejecución |
| backend/create_stock.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/ensure_ai_tables.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/ensure_roles.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/fix_permissions.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/init_db.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/manage_db.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_ai_intelligence.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_costo_unitario.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_daily_close.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_deduplication_table.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_financing.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_imei_audit_fields.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_imei_history.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_multistore_control.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_normal_card_rate.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_payment_breakdown.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_photo_metrics.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_rbac.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_replacement_imei.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_returns.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_trade_in_policies.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_tradein_details.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_transfer_payment_fields.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_transfer_receiving_fields.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_add_unique_transfer_reference.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_metrics_sqlite.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_sqlite_to_postgres.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migrate_to_locations_model.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/migration_ai.sql | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/populate_financing.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/postgres_test_utils.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, Lectura íntegra del coordinador en esta ejecución |
| backend/pytest.ini | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_tests.json |
| backend/requirements-dev.txt | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/requirements.txt | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/reset_admin.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/restore_database.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/seed_channel_credentials.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/start.bat | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/start.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/test_forecasting.ipynb | NOT_REVIEWED |  |
| backend/test_forecasting_direct.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/test_login_debug.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/test_script.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| backend/tests/__init__.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/tests/conftest.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_tests.json |
| backend/tests/helpers.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_ai_business_feature_guard_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_ai_candidate_product_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_ai_context_keyword_bound.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_ai_context_like_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_ai_customer_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_ai_intelligence_helpers.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_ai_order_product_query_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_ai_slug_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_ai_workflow.py | PARTIAL_REVIEWED | BLOQUE_security-ai.json |
| backend/tests/test_api_flow.py | NOT_REVIEWED |  |
| backend/tests/test_api_usage.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_auth_admin_role_guards.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_auth_rbac_invariants.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_auth_register_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_auth_security.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json, BLOQUE_tests.json |
| backend/tests/test_auth_user_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_auto_migrations.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_tests.json |
| backend/tests/test_business_integrity_middleware.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_channel_connection_capability.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_channel_health_access_control.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_channel_integrations.py | PARTIAL_REVIEWED | BLOQUE_security-ai.json |
| backend/tests/test_channel_monitoring_audit_access.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_channel_monitoring_status_channels.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_channel_webhook_delivery_integrity.py | PARTIAL_REVIEWED | BLOQUE_security-ai.json |
| backend/tests/test_channel_webhook_failed_session_release.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_channel_webhook_retry_state.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_faq_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_faq_search_keyword_bound.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_final_financial_and_order_concurrency.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_tests.json |
| backend/tests/test_final_integrity_regressions.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/tests/test_financing_bank_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_financing_bank_unicode_guards.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_financing_bank_unicode_versioned_guards.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_financing_recompute_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_historical_defective_imei_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_imei_admin_integrity.py | NOT_REVIEWED |  |
| backend/tests/test_imei_helpers.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_imei_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_imei_warranty_sale_date.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_initial_admin_setup_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_location_access_filters.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_tests.json |
| backend/tests/test_location_name_concurrency_integrity.py | NOT_REVIEWED |  |
| backend/tests/test_location_validation_errors.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_multistore_ops_integrity.py | NOT_REVIEWED |  |
| backend/tests/test_order_cancel_return_concurrency.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_order_currency.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_order_edit_pricing_integration.py | NOT_REVIEWED |  |
| backend/tests/test_order_edit_term_preservation.py | NOT_REVIEWED |  |
| backend/tests/test_order_financing_input_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_order_pricing_policy.py | NOT_REVIEWED |  |
| backend/tests/test_order_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_order_service_pricing_integration.py | NOT_REVIEWED |  |
| backend/tests/test_order_update_price_protection.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_photo_requests_flow.py | PARTIAL_REVIEWED | BLOQUE_security-ai.json |
| backend/tests/test_pricing_policy_migration.py | PARTIAL_REVIEWED | BLOQUE_deploy.json |
| backend/tests/test_product_purge_lock_order_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_product_restock_concurrency_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_product_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_product_update_sku_concurrency_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_production_guards.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_profile_settings_update_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_public_catalog_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_purchase_restock_lock_order_integrity.py | NOT_REVIEWED |  |
| backend/tests/test_rate_limiter.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_refund_reporting_period.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_reports_analytics.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json, BLOQUE_tests.json |
| backend/tests/test_restock_inventory_count_lock_compatibility.py | NOT_REVIEWED |  |
| backend/tests/test_restock_transfer_confirmation_lock_compatibility.py | NOT_REVIEWED |  |
| backend/tests/test_return_lock_order_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_return_promotion_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_tests.json |
| backend/tests/test_return_serial_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_tests.json |
| backend/tests/test_sales_profile_config_security.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_sales_profile_router_guards.py | NOT_REVIEWED |  |
| backend/tests/test_sales_profile_slug_concurrency_integrity.py | NOT_REVIEWED |  |
| backend/tests/test_second_pass_hardening.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_sqlite_to_postgres_migration.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_tests.json |
| backend/tests/test_startup_schema_lock.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_tests.json |
| backend/tests/test_stock_concurrency.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_tests.json |
| backend/tests/test_stock_history_access_stats.py | NOT_REVIEWED |  |
| backend/tests/test_stock_manager_invariants.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/tests/test_stock_transaction_helper_concurrency.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_tests.json |
| backend/tests/test_stock_transfer_router_guards.py | FULL_TEXT_REVIEWED | BLOQUE_business.json, BLOQUE_tests.json |
| backend/tests/test_super_admin_audit_filters.py | NOT_REVIEWED |  |
| backend/tests/test_super_admin_guards.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_super_admin_identity_concurrency.py | NOT_REVIEWED |  |
| backend/tests/test_super_admin_product_purge.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/tests/test_superuser_active_guard.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_supplier_name_concurrency_integrity.py | NOT_REVIEWED |  |
| backend/tests/test_supplier_search_integrity.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_supplier_validation_errors.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| backend/tests/test_transfer_creation_release_lock_compatibility.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/tests/test_upgrade_audit.py | PARTIAL_REVIEWED | BLOQUE_deploy.json |
| backend/tests/test_websocket_manager.py | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| backend/tests/test_websocket_security.py | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json, BLOQUE_tests.json |
| backend/upgrade_audit.py | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| browser_cleanup_script.js | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| check-production-setup.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| check_ai_tables.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| check_db_direct.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| check_luhn.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| check_roles.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| check_user_role.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| check_users_schema.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| cleanup.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| cleanup_system.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| cleanup_v2.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| components.json | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| deploy/.env.prod.example | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/GO_NO_GO_CHECKLIST.md | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/README.md | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/backup-now.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/backup-postgres.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/docker-compose.prod.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/dr-drill.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/nginx.conf | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/observability/alert_rules.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/observability/alertmanager.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/observability/grafana/provisioning/datasources/datasource.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/observability/prometheus.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/ops-healthcheck.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/prepare-prod-env.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/prod-gate.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/release-now.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/restore-backup.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/test-dr-drill.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/test-ops-healthcheck-timeout.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/test-prepare-prod-env.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/test-verify-offsite-backup.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/validate-prod.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/verify-offsite-backup.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/vps/README.md | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/vps/install-vps.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/vps/inventario-backup.cron | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/vps/inventario.service | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/vps/invjear-nginx-bootstrap.conf | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/vps/invjear-nginx-ssl.conf | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| deploy/vps/test-install-vps-db-preservation.sh | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| docker-compose.yml | FULL_TEXT_REVIEWED | BLOQUE_deploy.json |
| docs/ACTUALIZAR_INSTALACION_EXISTENTE.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/AI_REPORTING_SCOPE.md | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json, BLOQUE_utilities.json |
| docs/ARQUITECTURA.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/CONVENCION_NOMBRES.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/DEPENDENCY_MAINTENANCE.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/DEPLOYMENT.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/DEPLOYMENT_PROD.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/DIAGNOSTICO_MODELO_VENTAS.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/ESTADO_IA.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/EXECUCION_PARALELA_PLAN.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/GUIA_REFACTORIZACION.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/GUIA_TESTING.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/GUIA_TRANSFERENCIAS.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/INTEGRACION.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/INTEGRACION_N8N.md | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json, BLOQUE_utilities.json |
| docs/LIMITATIONS.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/MANUAL_COMPLETO.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/OPERACION.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/PRD.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/PREPRODUCTION_MAINTENANCE_PLAN.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/PRODUCCION_COMPLETA.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/PRODUCCION_FINAL.md | FULL_TEXT_REVIEWED | BLOQUE_deploy.json, BLOQUE_utilities.json |
| docs/PROD_INFRA_SECURITY.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/PROMPT_NEGOCIACION_BOT.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/RBAC_REFACTOR_PLAN.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/REFACTORING_STATUS.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/RESUMEN_MEJORAS.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/SEGURIDAD.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/SYNC_STRATEGY.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/TESTING_PLAN.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/TESTING_RESULTS.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/VALIDACION.md | NOT_REVIEWED | BLOQUE_utilities.json |
| docs/VALIDATION_PLAN.md | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| docs/n8n/whatsapp_ai_flow.json | FULL_TEXT_REVIEWED | BLOQUE_security-ai.json |
| eslint.config.js | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| index.html | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| inspect_last_order.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| package-lock.json | PARTIAL_REVIEWED | BLOQUE_utilities.json |
| package.json | FULL_TEXT_REVIEWED | BLOQUE_utilities.json, Lectura íntegra del coordinador en esta ejecución |
| playwright.config.ts | FULL_TEXT_REVIEWED | BLOQUE_utilities.json, Lectura íntegra del coordinador en esta ejecución |
| pytest.ini | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| reset_system.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| runtime.config.json | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| setup-postgres.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| setup-production.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| setup-sentry.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| simple_tsc.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| simulate_whatsapp_flow.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| spark.meta.json | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/App.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/ErrorFallback.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/__tests__/App.saleCompletion.test.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json, BLOQUE_tests.json |
| src/components/AIChatOrchestratorDialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/AIForecastingDialog.tsx | NOT_REVIEWED |  |
| src/components/AIProfileConfigDialog.tsx | NOT_REVIEWED |  |
| src/components/AIStatusDialog.tsx | NOT_REVIEWED |  |
| src/components/AIStatusWidget.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/AITrainingCenter.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/AdvancedSearchDialog.tsx | NOT_REVIEWED |  |
| src/components/BackendConnectionCheck.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/ChannelHealthDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/CustomerHistoryDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/CustomerInsights.tsx | NOT_REVIEWED |  |
| src/components/CustomizeShortcutsDialog.tsx | NOT_REVIEWED |  |
| src/components/DailyCloseDialog.tsx | NOT_REVIEWED |  |
| src/components/DashboardStats.tsx | NOT_REVIEWED |  |
| src/components/EditOrderDialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/EditProductDialog.tsx | NOT_REVIEWED |  |
| src/components/EditProfileDialog.tsx | NOT_REVIEWED |  |
| src/components/FinancingSettings.tsx | NOT_REVIEWED |  |
| src/components/ForecastingWidget.tsx | NOT_REVIEWED |  |
| src/components/HealthCheckDialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/IMEIHistoryDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/IMEIListDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/ImportProductsDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/KeyboardShortcutsDialog.tsx | NOT_REVIEWED |  |
| src/components/LocationsList.tsx | NOT_REVIEWED |  |
| src/components/LoginDialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/LoginPage.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/LowStockAlert.tsx | NOT_REVIEWED |  |
| src/components/LowStockReportDialog.tsx | NOT_REVIEWED |  |
| src/components/ManageFAQsDialog.tsx | NOT_REVIEWED |  |
| src/components/ManageSuppliersDialog.tsx | NOT_REVIEWED |  |
| src/components/ManageUsersDialog.tsx | NOT_REVIEWED |  |
| src/components/MultiStoreControlDialog.tsx | NOT_REVIEWED |  |
| src/components/NewOrderDialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/NewProductDialog.tsx | NOT_REVIEWED |  |
| src/components/NewProfileDialog.tsx | NOT_REVIEWED |  |
| src/components/NotificationCenter.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/NotificationSettingsDialog.tsx | NOT_REVIEWED |  |
| src/components/OptimizationInsightsDialog.tsx | NOT_REVIEWED |  |
| src/components/OrderCard.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/PendingTradeInsDialog.tsx | NOT_REVIEWED |  |
| src/components/PendingTransfersDialog.tsx | NOT_REVIEWED |  |
| src/components/PhotoRequestsDashboard.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/PhotoRequestsDashboardDialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/PrintLabelsDialog.tsx | NOT_REVIEWED |  |
| src/components/ProductCard.tsx | NOT_REVIEWED |  |
| src/components/ProductIMEIRegistryDialog.tsx | NOT_REVIEWED |  |
| src/components/ProductLabel.tsx | NOT_REVIEWED |  |
| src/components/ProfileCard.tsx | NOT_REVIEWED |  |
| src/components/ProfileConfigPrompt.tsx | NOT_REVIEWED |  |
| src/components/ProfileDetailsDialog.tsx | NOT_REVIEWED |  |
| src/components/ProfileSettingsDialog.tsx | NOT_REVIEWED |  |
| src/components/ProfileSettingsSummary.tsx | NOT_REVIEWED |  |
| src/components/ProfileSetupGuide.tsx | NOT_REVIEWED |  |
| src/components/ProfilesConfigSummary.tsx | NOT_REVIEWED |  |
| src/components/PublicCatalog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/ReportsDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/RestockProductDialog.tsx | NOT_REVIEWED |  |
| src/components/ReturnDialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/ReturnsListDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/SalesHistoryDialog.tsx | NOT_REVIEWED |  |
| src/components/SalesProfilesList.tsx | NOT_REVIEWED |  |
| src/components/SettingsDialog.tsx | NOT_REVIEWED |  |
| src/components/StockByLocationDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/StockHistoryDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/StorageDiagnosticDialog.tsx | NOT_REVIEWED |  |
| src/components/SuperAdminControlPanelDialog.tsx | NOT_REVIEWED |  |
| src/components/SyncIndicator.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/SyncSettingsDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/TradeInPoliciesDialog.tsx | NOT_REVIEWED |  |
| src/components/TransferListDialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/TransferStockDialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/components/ValidationCodeDialog.tsx | NOT_REVIEWED |  |
| src/components/WarrantyCheckDialog.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/components/__tests__/DailyCloseDialog.test.tsx | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/components/__tests__/LoginDialog.test.tsx | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/components/__tests__/LoginPage.test.tsx | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/components/__tests__/NewOrderDialog.test.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json, BLOQUE_tests.json |
| src/components/__tests__/ReturnDialog.test.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json, BLOQUE_tests.json |
| src/components/__tests__/SuperAdminControlPanelDialog.test.tsx | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/components/__tests__/TransferListDialog.test.tsx | FULL_TEXT_REVIEWED | BLOQUE_frontend.json, BLOQUE_tests.json |
| src/components/__tests__/ValidationCodeDialog.test.tsx | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/components/forms/RoleSelect.tsx | NOT_REVIEWED |  |
| src/components/ui/accordion.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/alert-dialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/alert.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/aspect-ratio.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/avatar.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/badge.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/breadcrumb.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/button.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/calendar.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/card.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/carousel.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/chart.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/checkbox.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/collapsible.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/command.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/context-menu.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/dialog.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/drawer.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/dropdown-menu.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/form.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/hover-card.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/input-otp.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/input.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/label.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/menubar.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/navigation-menu.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/pagination.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/popover.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/progress.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/radio-group.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/resizable.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/scroll-area.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/select.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/separator.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/sheet.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/sidebar.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/skeleton.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/slider.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/sonner.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/switch.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/table.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/tabs.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/textarea.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/toggle-group.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/toggle.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/components/ui/tooltip.tsx | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| src/hooks/__tests__/use-forecasting.test.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json, BLOQUE_tests.json |
| src/hooks/use-ai-status.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-forecasting.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-health-check.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-initialize-data.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-keyboard-shortcuts.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-kv.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-mobile.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-optimization-alerts.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-optimization-insights.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-photo-request-websocket.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-rbac.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-realtime-sync.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-sync-detection.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/hooks/use-virtual-scroll.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/index.css | NOT_REVIEWED |  |
| src/lib/__tests__/apiClient.test.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json, BLOQUE_tests.json |
| src/lib/__tests__/appViewModel.test.ts | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/lib/__tests__/dataInitializer.test.ts | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/lib/__tests__/importUtils.test.ts | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/lib/__tests__/inventoryService.local.test.ts | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/lib/__tests__/orderStatusActions.test.ts | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/lib/__tests__/phoneValidator.test.ts | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/lib/aiForecasting.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/apiClient.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/appViewModel.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/businessInsightsFallback.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/chatOrchestrator.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/config.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/dataInitializer.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/exportUtils.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/healthCheck.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/icon-proxies/lucide.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/icon-proxies/phosphor.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/importUtils.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/initialData.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/inventoryService.ts | NOT_REVIEWED |  |
| src/lib/inventoryServiceFactory.production.test.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json, BLOQUE_tests.json |
| src/lib/inventoryServiceFactory.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json, CONTINUACION_02.json |
| src/lib/keyboardShortcuts.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/kvStorage.manual.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/kvStorage.test.ts | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/lib/kvStorage.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/labelPrint.ts | NOT_REVIEWED |  |
| src/lib/optimizationAnalytics.ts | NOT_REVIEWED |  |
| src/lib/orderStatus.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/orderStatusActions.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/pdfExport.ts | NOT_REVIEWED |  |
| src/lib/phoneValidator.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/priceFormatter.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/profileUtils.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/reportUtils.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/runtimePolicy.test.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json, BLOQUE_tests.json |
| src/lib/runtimePolicy.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/syncJournal.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/syncService.ts | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/lib/types.ts | PARTIAL_REVIEWED | BLOQUE_frontend.json |
| src/lib/utils.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/validation/__tests__/transferStockSchema.test.ts | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/lib/validation/importProductsSchema.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/validation/orderFormSchema.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/validation/tradeInActivationSchema.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/validation/tradeInPolicySchema.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/validation/transferStockSchema.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/lib/validation/types.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| src/main.css | NOT_REVIEWED |  |
| src/main.tsx | FULL_TEXT_REVIEWED | CONTINUACION_02.json |
| src/styles/theme.css | NOT_REVIEWED |  |
| src/test/msw/handlers.ts | NOT_REVIEWED |  |
| src/test/msw/server.ts | NOT_REVIEWED |  |
| src/test/setup.ts | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| src/vite-end.d.ts | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| start-all-postgres.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| start-all.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| start-backend-codespaces.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| start-backend.bat | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| start-backend.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| start-frontend.bat | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| start-frontend.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| tailwind.config.js | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| test-system.sh | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| test_luhn.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| test_n8n_simulation.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| tests/browser/authenticated-staging.spec.ts | FULL_TEXT_REVIEWED | Lectura íntegra del coordinador en esta ejecución |
| tests/browser/financing.spec.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| tests/browser/receipt.spec.ts | FULL_TEXT_REVIEWED | Lectura íntegra del coordinador en esta ejecución |
| tests/browser/sale.spec.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| tests/browser/staging-smoke.spec.ts | FULL_TEXT_REVIEWED | Lectura íntegra del coordinador en esta ejecución |
| tests/browser/transfer-lifecycle.spec.ts | FULL_TEXT_REVIEWED | BLOQUE_frontend.json |
| tests/e2e/test_business_flows_e2e.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| tests/e2e/test_postgres_runtime_e2e.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| tests/e2e/test_runtime_e2e.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| tests/test_health_endpoints.py | FULL_TEXT_REVIEWED | BLOQUE_tests.json |
| theme.json | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| tsconfig.json | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| typings/apscheduler/schedulers/asyncio/__init__.pyi | NOT_REVIEWED |  |
| typings/apscheduler/triggers/cron/__init__.pyi | NOT_REVIEWED |  |
| verify_learning.py | FULL_TEXT_REVIEWED | BLOQUE_utilities.json |
| vite.config.ts | FULL_TEXT_REVIEWED | BLOQUE_utilities.json, Lectura íntegra del coordinador en esta ejecución |
