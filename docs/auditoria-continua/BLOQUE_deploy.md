# Auditoría deploy/database

SHA: `dba6763391d12c6c91c9904cba36725710f9280a`. Sólo lectura; sin despliegues/restauraciones/truncate reales.

## Hallazgos

### OPS-01 — HIGH — Backup automático Compose escribe fuera del volumen persistente

Estado: CONFIRMED_STATIC.

Archivos: deploy/docker-compose.prod.yml:73-77, deploy/.env.prod.example:44, deploy/prepare-prod-env.sh:297, deploy/backup-postgres.sh:5,11,17-20

Evidencia: Env compartido BACKUP_DIR=/app/backups; backup sólo monta backend_backups:/backups. Script respeta BACKUP_DIR. Offsite y healthcheck leen /backups.

Impacto: Dumps diarios quedan en filesystem efímero del container, no se replican; al recrear backup se pierden. Gate espera backups que no aparecen.

Repro: Preparar env estándar y resolver configuración de backup: destino efectivo /app/backups no es mount /backups. No Docker real ejecutado.

Recomendación: Override environment BACKUP_DIR=/backups en servicio backup; probar dump sintético por stack y persistencia tras recreación.

Pruebas: Los cinco shell tests pasan porque no comprueban wiring env+volume.

### OPS-02 — HIGH — Healthcheck operativo exige una ruta que nginx bloquea

Estado: CONFIRMED_STATIC.

Archivos: deploy/ops-healthcheck.sh:66, deploy/nginx.conf:28-30, deploy/release-now.sh:100

Evidencia: curl -fsS http://127.0.0.1:${frontend_port}/api/metrics versus location = /api/metrics return 404. set -e aborta.

Impacto: Release y healthcheck fallan incluso con backend saludable, antes de verificar backups/provenance.

Repro: Comparación exacta de ruta y server config; no HTTP producción ejecutado.

Recomendación: Consultar métricas desde backend dentro de red Docker; mantener bloqueo público y añadir integration test del nginx real.

Pruebas: test-ops-healthcheck-timeout sustituye curl por éxito incondicional, oculta conflicto.

### OPS-03 — HIGH — Backup VPS anuncia éxito aunque pg_dump falle

Estado: REPRODUCED.

Archivos: backend/backup_database.sh:105-121,183-192

Evidencia: create_backup se evalúa como condición if: Bash desactiva errexit dentro de función. pipeline pg_dump exit42 seguido gzip es fallido pero se ignora, se crea sidecar y último log retorna0.

Impacto: Backups SQL vacíos/incompletos certificados por checksum, falsa señal de recuperación, además se borran backups antiguos.

Repro: pg_dump sintético exit42 en PATH y BACKUP_DIR temporal. Exit script0; SQL descomprimido0 bytes; .sha256 existe; SUCCESS. Evidencia /tmp/audit-deploy-backup-repro.json.

Recomendación: Validar pipeline explícitamente con if ! ...; escribir temporal, comprobar SQL no vacío/gzip, publicar atómicamente sólo tras éxito; no ejecutar retención tras fallo.

Pruebas: Reproducción fresca ejecutada; no DB ni backups reales.

### OPS-04 — HIGH — Migración monetaria SQLite bloquea arranque por parámetros Decimal

Estado: REPRODUCED.

Archivos: backend/app/utils/pricing_policy_migration.py:215-217,225-232, backend/app/main.py:100-103

Evidencia: SQL text sin tipo enlaza decimal.Decimal a sqlite3, que rechaza binding.

Impacto: Actualización legado SQLite con órdenes USD falla startup, no sirve tráfico.

Repro: DB in-memory con ai_profile_configs/products/orders/order_items, producto100USD, orden100. ProgrammingError Error binding parameter1 type decimal.Decimal not supported; /tmp/audit-pricing-repro.py + /tmp/audit-deploy-pricing-repro.json.

Recomendación: Usar parámetros tipados Numeric compatibles o serialización decimal exacta para SQLite, añadir prueba SQLite de migración monetaria.

Pruebas: Repro venv exact requirements, Python3.12; tests actuales monetarios usan fixture PostgreSQL.

### OPS-05 — HIGH — Bootstrap VPS nuevo no genera SETUP_TOKEN obligatorio

Estado: CONFIRMED_STATIC.

Archivos: deploy/vps/install-vps.sh:302-353,365-371, backend/app/config.py:129-132

Evidencia: Here-doc backend/.env no contiene SETUP_TOKEN; Settings en production exige al menos32 caracteres. init_db importa app.database/settings.

Impacto: Instalación nueva falla inicialización/arranque pese a documentación de instalador completo.

Repro: Ejecutar Settings con variables del here-doc y sin token: guard producción rechaza. No instalador real ejecutado.

Recomendación: Generar token seguro en bootstrap y documentar uso inicial, probar import config con env generado sintético.

Pruebas: test-install-vps-db-preservation cubre reejecución, no config bootstrap nuevo.

### OPS-06 — HIGH — Ruta env relativa recomendada se invalida al cambiar directorio en release

Estado: CONFIRMED_STATIC.

Archivos: deploy/release-now.sh:8,95-97, deploy/README.md:159, deploy/ops-healthcheck.sh:8,45, deploy/backup-now.sh:6, deploy/restore-backup.sh:6

Evidencia: ENV_FILE conserva ./deploy/.env.prod; validadores realpath sólo en procesos hijos. Después cd deploy docker --env-file ./deploy/.env.prod busca deploy/deploy/.env.prod. PROD_ENV_FILE relativa también se resuelve respecto de compose.

Impacto: Comando de lanzamiento documentado falla después de gates costosos; otros entrypoints relativos pueden fallar Compose.

Repro: Desde raíz release-now ./deploy/.env.prod; seguir resolución cwd antes/después cd, sin desplegar.

Recomendación: Normalizar ENV_FILE a ruta absoluta tras validar existencia en todos entrypoints. Añadir fake docker que verifica paths.

Pruebas: prepare env test cubre validate-prod normalization, no parent release.

### OPS-07 — HIGH — Restore no reemplaza BD existente y no es atómico

Estado: CONFIRMED_STATIC.

Archivos: deploy/restore-backup.sh:26-41, deploy/backup-now.sh:22-24, deploy/backup-postgres.sh:24-30

Evidencia: Dumps plain pg_dump sin --clean; restore psql ON_ERROR_STOP sin single transaction ni target limpio. En schema existente primer CREATE falla; comandos previos a cualquier fallo quedan commit.

Impacto: Procedimiento documentado como sobrescritura no restaura instancia existente; fallo en DB vacía puede dejar esquema parcialmente restaurado.

Repro: Backup generado contiene CREATE TABLE; destino con tabla homónima produce already exists, ON_ERROR_STOP corta. No restore real autorizado/ejecutado.

Recomendación: Procedimiento explícito restauración a nueva BD limpia con verificación y switch; exigir checksum de archivo actual por hash, transacción donde viable; mantenimiento previo y rollback documentado.

Pruebas: DR usa container PostgreSQL limpio; no prueba restore-backup existente.

### OPS-08 — HIGH — --truncate migra después de confirmar truncado en transacción separada

Estado: CONFIRMED_STATIC.

Archivos: backend/migrate_sqlite_to_postgres.py:124-132,254-255,270-280

Evidencia: TRUNCATE ... CASCADE se commit en _truncate_tables antes de iniciar copia target_engine.begin. Si faltan campos/falla FK/copia, rollback sólo revierte inserciones, destino anterior queda vacío.

Impacto: Fallo migración con reemplazo autorizado pierde datos anteriores del destino y cascadas dependientes; sólo existe backup SQLite fuente.

Repro: Destino con datos, --truncate, fuente sin campo obligatorio: _required_target_columns... falla después del commit truncate. No truncate real ejecutado.

Recomendación: Preflight completo antes de borrar; integrar truncate+insert en misma transacción, backup del destino y reparar sequences antes de publicar éxito.

Pruebas: test_sqlite_to_postgres_migration.py sólo helpers SQLite; no fallo de copia tras truncate PostgreSQL.

### OPS-09 — MEDIUM — Utilidad demo de credenciales elimina otras configuraciones del perfil

Estado: CONFIRMED_STATIC.

Archivos: backend/seed_channel_credentials.py:31-51,183-196,239-244

Evidencia: Cuando JSON incluye channel_integrations dict, parser devuelve únicamente ese campo; populate y clear pretenden preservar otros campos pero trabajan con objeto recortado. Config {exchange_rate:24.5,channel_integrations:{...}} pierde exchange_rate; --clear devuelve None.

Impacto: Operador que ejecuta utilidad sobre perfiles existentes pierde tipo de cambio y otras políticas de negocio/configuración. No es ejecutada por startup/deploy canonical.

Repro: Trazado estático de dict input con exchange_rate e integrations por parser; no utilidad ni DB real ejecutadas.

Recomendación: Preservar copia completa del dict y normalizar sólo channel_integrations; rechazar producción para demo; tests para preservar configuraciones con --populate/--clear.

Pruebas: Lectura completa; sin ejecución según ampliación sólo lectura.

## Pruebas ejecutadas

- `bash deploy/test-prepare-prod-env.sh`: exit 0; Production env bootstrap tests OK

- `bash deploy/vps/test-install-vps-db-preservation.sh`: exit 0; VPS installer DB credential preservation tests OK

- `bash deploy/test-verify-offsite-backup.sh`: exit 0; Off-site backup verifier tests OK

- `bash deploy/test-ops-healthcheck-timeout.sh`: exit 0; Off-site healthcheck timeout test OK (1s)

- `bash deploy/test-dr-drill.sh`: exit 0; DR drill hardening tests OK

Repros previas: pg_dump falso exit42 produjo SQL vacío+SUCCESS; pricing SQLite falló binding Decimal. Ampliación: ninguna utilidad ejecutada.

## Cobertura EXACTA

```json

{
  "complete_static": [
    ".github/dependabot.yml",
    ".github/workflows/browser-e2e.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/dr-drill.yml",
    ".github/workflows/release-gate.yml",
    "AGENTS.md",
    "CHECKLIST_PRODUCCION.md",
    "COMIENZA_AQUI.md",
    "DEPLOY_CHECKLIST.md",
    "Dockerfile.frontend",
    "README.md",
    "backend/Dockerfile",
    "backend/QUICKSTART.md",
    "backend/README.md",
    "backend/app/database.py",
    "backend/app/startup_schema_lock.py",
    "backend/app/utils/auto_migrations.py",
    "backend/app/utils/pricing_policy_migration.py",
    "backend/apply_migrations_direct.py",
    "backend/backup_database.sh",
    "backend/check_channels_config.py",
    "backend/check_db.py",
    "backend/check_faqs.py",
    "backend/check_production_readiness.py",
    "backend/conftest.py",
    "backend/create_stock.py",
    "backend/ensure_ai_tables.py",
    "backend/ensure_roles.py",
    "backend/fix_permissions.py",
    "backend/init_db.py",
    "backend/manage_db.py",
    "backend/migrate_add_ai_intelligence.py",
    "backend/migrate_add_costo_unitario.py",
    "backend/migrate_add_daily_close.py",
    "backend/migrate_add_deduplication_table.py",
    "backend/migrate_add_financing.py",
    "backend/migrate_add_imei_audit_fields.py",
    "backend/migrate_add_imei_history.py",
    "backend/migrate_add_multistore_control.py",
    "backend/migrate_add_normal_card_rate.py",
    "backend/migrate_add_payment_breakdown.py",
    "backend/migrate_add_photo_metrics.py",
    "backend/migrate_add_rbac.py",
    "backend/migrate_add_replacement_imei.py",
    "backend/migrate_add_returns.py",
    "backend/migrate_add_trade_in_policies.py",
    "backend/migrate_add_tradein_details.py",
    "backend/migrate_add_transfer_payment_fields.py",
    "backend/migrate_add_transfer_receiving_fields.py",
    "backend/migrate_add_unique_transfer_reference.py",
    "backend/migrate_metrics_sqlite.py",
    "backend/migrate_sqlite_to_postgres.py",
    "backend/migrate_to_locations_model.py",
    "backend/migration_ai.sql",
    "backend/populate_financing.py",
    "backend/postgres_test_utils.py",
    "backend/pytest.ini",
    "backend/requirements-dev.txt",
    "backend/requirements.txt",
    "backend/reset_admin.py",
    "backend/restore_database.sh",
    "backend/seed_channel_credentials.py",
    "backend/start.bat",
    "backend/start.sh",
    "backend/test_forecasting_direct.py",
    "backend/test_login_debug.py",
    "backend/test_script.py",
    "backend/tests/test_sqlite_to_postgres_migration.py",
    "backend/tests/test_startup_schema_lock.py",
    "backend/upgrade_audit.py",
    "deploy/.env.prod.example",
    "deploy/GO_NO_GO_CHECKLIST.md",
    "deploy/README.md",
    "deploy/backup-now.sh",
    "deploy/backup-postgres.sh",
    "deploy/docker-compose.prod.yml",
    "deploy/dr-drill.sh",
    "deploy/nginx.conf",
    "deploy/observability/alert_rules.yml",
    "deploy/observability/alertmanager.yml",
    "deploy/observability/grafana/provisioning/datasources/datasource.yml",
    "deploy/observability/prometheus.yml",
    "deploy/ops-healthcheck.sh",
    "deploy/prepare-prod-env.sh",
    "deploy/prod-gate.sh",
    "deploy/release-now.sh",
    "deploy/restore-backup.sh",
    "deploy/test-dr-drill.sh",
    "deploy/test-ops-healthcheck-timeout.sh",
    "deploy/test-prepare-prod-env.sh",
    "deploy/test-verify-offsite-backup.sh",
    "deploy/validate-prod.sh",
    "deploy/verify-offsite-backup.sh",
    "deploy/vps/README.md",
    "deploy/vps/install-vps.sh",
    "deploy/vps/inventario-backup.cron",
    "deploy/vps/inventario.service",
    "deploy/vps/invjear-nginx-bootstrap.conf",
    "deploy/vps/invjear-nginx-ssl.conf",
    "deploy/vps/test-install-vps-db-preservation.sh",
    "docker-compose.yml",
    "docs/PRODUCCION_FINAL.md"
  ],
  "partial_static": [
    "backend/app/main.py",
    "backend/app/config.py",
    "backend/app/config_production.py",
    "backend/tests/test_auto_migrations.py",
    "backend/tests/test_upgrade_audit.py",
    "backend/tests/test_pricing_policy_migration.py"
  ],
  "not_present": [
    "No tracked Alembic env/versions/migrations found by rg --files; dependency alembic exists but current canonical path is auto_migrations"
  ],
  "not_verified": [
    "Actual Docker Compose runtime",
    "PostgreSQL truncate/restore failure reproduction",
    "Actual remote backup destination/content",
    "Actual staging DR",
    "VPS running version and environment",
    "GitHub checks/branch and tag rulesets",
    "Alertmanager pinned binary support for --config.expand-env"
  ],
  "not_reviewed_paths_in_backend_root": [
    "backend/api-examples.json",
    "backend/test_forecasting.ipynb"
  ],
  "method": "complete_static significa lectura completa del archivo y razonamiento estático; no implica prueba de todos sus comportamientos. Lista resuelta explícitamente, sin grupos. deploy test files leídos íntegros en ampliación; los cinco ejecutados previamente contra mocks."
}

```

## Riesgos adicionales

```json

[
  {
    "status": "STATIC_RISK",
    "files": [
      "backend/app/utils/pricing_policy_migration.py:151-168,195-239"
    ],
    "description": "Legacy USD detection infers persisted currency from CURRENT mutable catalog price/currency and CURRENT exchange rate; cannot prove order actually USD. A later price increase/current currency change can misclassify HNL historical rows and multiply totals. Require immutable currency/rate metadata or operator approved candidate report before one-shot conversion."
  },
  {
    "status": "STATIC_LIMITATION",
    "files": [
      "deploy/dr-drill.sh:110-124"
    ],
    "description": "RPO inferred from local mtime, which can change when downloading/copying old backup; no dump timestamp proof. RTO measures psql only, not full recovery."
  },
  {
    "status": "STATIC_LIMITATION",
    "files": [
      "backend/upgrade_audit.py:206-247"
    ],
    "description": "Snapshot conn default PostgreSQL READ COMMITTED means counts/fingerprints/metrics across queries can see distinct concurrent states. Use maintenance/quiescence or repeatable read snapshot when comparing live systems."
  }
]

```

## Legado/manual: no equivalen a falla del despliegue canónico

```json

[
  {
    "paths": [
      "backend/manage_db.py",
      "backend/migrate_add_rbac.py",
      "backend/migrate_add_financing.py",
      "backend/migrate_add_normal_card_rate.py",
      "backend/migrate_add_tradein_details.py",
      "backend/migrate_add_ai_intelligence.py",
      "backend/migrate_add_daily_close.py",
      "backend/migration_ai.sql"
    ],
    "status": "LEGACY_STATIC_ONLY",
    "evidence": "Manager descubre todos migrate_*.py; mezcla scripts PRAGMA/AUTOINCREMENT/DATETIME SQLite con PostgreSQL y scripts one-shot. Algunos capturan excepción y retornan0, otros engine.connect no commit. Canonical docs actuales ejecutan auto_migrations startup, no este manager.",
    "recommendation": "Etiquetar legacy/manual, retirar de discover-all o consolidar schema upgrades soportados en runner canonical y validar cada baseline PostgreSQL."
  },
  {
    "paths": [
      "backend/migrate_to_locations_model.py",
      "backend/create_stock.py"
    ],
    "status": "LEGACY_STATIC_ONLY",
    "evidence": "Locations migration usa ORM actual contra schema antiguo; create_all no ALTER existentes. Crea Location nueva por Profile siempre y sólo copia cantidad_disponible, omite reservada/transito/defectuosa. create_stock distribuye entero product.stock//locations y pierde resto, además referencia campos antiguos del modelo. No invocados por canonical startup.",
    "recommendation": "No reutilizar en upgrade real sin baseline antiguo reproducido, inventario conciliado y preflight+rollback; marcar históricos."
  },
  {
    "paths": [
      "backend/reset_admin.py",
      "backend/migrate_add_rbac.py",
      "backend/test_login_debug.py"
    ],
    "status": "MANUAL_OPERATOR_RISK",
    "evidence": "reset_admin fuerza admin123 y superuser sin entorno/confirmación; RBAC legacy crea admin123; login debug imprime token completo. No reachable API ni invocados por canonical startup.",
    "recommendation": "Eliminar credenciales fijas de utilities; requerir password explícito/seguro y bloquear entornos production para scripts demo."
  },
  {
    "paths": [
      "backend/check_production_readiness.py",
      "backend/check_channels_config.py",
      "backend/README.md",
      "backend/QUICKSTART.md"
    ],
    "status": "DOC_OR_HELPER_DRIFT",
    "evidence": "Readiness puede declarar listo en development y no verifica continuidad real; channels trata META_APP_SECRET ausente warning aunque producción falla cerrado; README/QUICKSTART contienen endpoints sin auth y guías antiguas. Runbook canónico explícitamente prevalece y no llama readiness legacy como release gate.",
    "recommendation": "Rotular alcance dev/legacy, redirigir runbook canónico; no usar helper como evidencia de producción."
  }
]

```