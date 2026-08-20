# Producción Final — Runbook Canónico

Última revisión: 2026-08-20.

Este documento es la fuente canónica para desplegar, verificar y recuperar el sistema. Si otra guía histórica contradice este archivo, prevalece este runbook.

## 1. Invariantes de producción

1. PostgreSQL es obligatorio; SQLite no es válido como base productiva.
2. El frontend productivo trabaja exclusivamente contra la API.
3. Si la API no está disponible, el frontend se bloquea y no continúa con datos locales.
4. `DEBUG=false` y `ENVIRONMENT=production`.
5. CORS y hosts deben estar restringidos al dominio real.
6. Operaciones destructivas están deshabilitadas por defecto.
7. Backups deben existir tanto en el host como fuera del host.
8. Una migración fallida detiene el backend.
9. Un release requiere CI verde y restauración verificada.
10. No se crea un tag estable `v*` mientras el Issue #38 siga abierto o falte el ruleset de tags requerido.

## 2. Preparar el entorno

Desde la raíz:

```bash
APP_DOMAIN=inventario.tudominio.com ./deploy/prepare-prod-env.sh
```

El script genera secretos locales cuando es posible y crea `deploy/.env.prod` con permisos restrictivos.

Revisa manualmente:

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `CHANNEL_ENCRYPTION_KEY`
- `SETUP_TOKEN`
- `DESTRUCTIVE_OPERATION_TOKEN`
- `ALLOWED_HOSTS`
- `CORS_ORIGINS`
- `GRAFANA_ADMIN_PASSWORD`
- `BACKUP_RCLONE_DESTINATION`
- credenciales `RCLONE_CONFIG_*` del proveedor off-site
- `SENTRY_DSN`, SMTP, OpenAI, N8N/Meta sólo si esas funciones se usan

Nunca confirmes `.env.prod` ni secretos en Git.

## 3. Backup off-site

El servicio `backup` crea dumps PostgreSQL comprimidos y checksum SHA-256 en el volumen `backend_backups`.

El servicio `backup-offsite` comparte ese volumen en modo lectura y replica los archivos mediante rclone.

Ejemplo S3-compatible:

```env
REQUIRE_OFFSITE_BACKUP=true
BACKUP_RCLONE_DESTINATION=offsite:mi-bucket/inventory
BACKUP_OFFSITE_INTERVAL_SECONDS=3600
RCLONE_CONFIG_OFFSITE_TYPE=s3
RCLONE_CONFIG_OFFSITE_PROVIDER=AWS
RCLONE_CONFIG_OFFSITE_ACCESS_KEY_ID=...
RCLONE_CONFIG_OFFSITE_SECRET_ACCESS_KEY=...
RCLONE_CONFIG_OFFSITE_REGION=us-east-1
```

La configuración también puede usar SFTP, Google Drive u otro backend soportado por rclone. Las credenciales pertenecen al secret manager/archivo de entorno productivo, no al repositorio.

## 4. Validar configuración

```bash
./deploy/validate-prod.sh ./deploy/.env.prod
```

El gate rechaza, entre otros:

- placeholders sin reemplazar;
- SQLite;
- `DEBUG=true`;
- CORS/hosts abiertos;
- secretos demasiado cortos;
- configuración destructiva sin token dedicado;
- parámetros de backup inválidos;
- falta de destino off-site cuando es obligatorio;
- errores de composición Docker.

No continúes si este comando falla.

## 5. Levantar producción

```bash
cd deploy

docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  --profile backup \
  --profile backup-offsite \
  up -d --build
```

Para observabilidad completa agrega:

```bash
--profile monitoring
```

## 6. Verificaciones inmediatas

Comprueba contenedores:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

Readiness:

```bash
curl -fsS https://inventario.tudominio.com/api/ready
```

Health:

```bash
curl -fsS https://inventario.tudominio.com/api/health
```

Flujo manual mínimo:

1. Login administrativo.
2. Consultar inventario.
3. Crear producto/stock de prueba controlado.
4. Crear una orden.
5. Confirmar descuento de stock/IMEI.
6. Cancelar el caso de prueba si corresponde y comprobar reversión.
7. Probar una transferencia entre ubicaciones.
8. Revisar auditoría y cierre diario.
9. Verificar que un usuario limitado no vea/edite ubicaciones ajenas.

## 7. Migraciones

Al iniciar el backend:

1. `Base.metadata.create_all()` garantiza tablas faltantes para instalaciones nuevas.
2. `run_auto_migrations()` crea/consulta `schema_migrations`.
3. Sólo ejecuta migraciones de compatibilidad pendientes.
4. Registra el ID de cada migración aplicada.
5. Valida tablas y columnas críticas.
6. Ante cualquier error, el proceso falla y no sirve tráfico.

Para futuras modificaciones de esquema:

- añade una función idempotente a `backend/app/utils/auto_migrations.py`;
- asigna un ID nuevo y ordenado en `MIGRATIONS`;
- añade/actualiza pruebas en `backend/tests/test_auto_migrations.py`;
- nunca modifiques el significado de un ID ya liberado.

## 8. Backups y restauración

Verifica archivos locales:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backup sh -lc 'ls -lh /backups'
```

Cada `.sql.gz` publicado debe tener `.sql.gz.sha256`.

Antes de un release importante, ejecuta una restauración en staging. El repositorio incluye:

- `deploy/dr-drill.sh`
- `.github/workflows/dr-drill.yml`

El workflow requiere secretos de staging y está programado semanalmente. Una ejecución fallida debe tratarse como incidente de continuidad, no como warning cosmético.

## 9. CI y release gate

PR a `main` ejecuta `.github/workflows/ci.yml` con:

- lint;
- frontend tests/coverage;
- backend tests sobre PostgreSQL;
- E2E de runtime/negocio/PostgreSQL;
- auditoría de dependencias;
- Trivy sobre código e imágenes según el workflow vigente.

Antes de etiquetar una versión estable, ejecuta `Release Gate` **manualmente** sobre el `main` aprobado y exige resultado verde. Después de cumplir todos los requisitos de release, el tag `v*` puede disparar el gate nuevamente como comprobación adicional.

No uses la ejecución disparada por un tag como única protección de procedencia: un tag sobre un commit histórico ejecuta el workflow versionado que exista en ese commit. Por eso, antes de crear el tag debes verificar que el SHA objetivo coincide exactamente con el HEAD aprobado de `main`, que el Issue #38 ya está cerrado y que el ruleset de tags está activo.

## 10. Protección de `main` y tags estables

Configuración requerida para `main` en GitHub:

- Require a pull request before merging.
- Require status checks to pass before merging.
- Require branches to be up to date before merging, si el flujo del equipo lo permite.
- Block force pushes.
- Block deletions.
- Aplicar también a administradores si se desea máxima disciplina.

Los nombres exactos de checks deben seleccionarse después de observar los checks reales del PR final para no configurar nombres obsoletos.

Configuración requerida para releases estables:

- Crear en **Settings → Rules → Rulesets** un **Tag ruleset** activo.
- Aplicarlo al patrón `v*`.
- Activar **Restrict creations**.
- Activar **Restrict updates**.
- Activar **Restrict deletions**.
- Mantener el bypass lo más limitado posible.
- No usar el bypass hasta que el Issue #38 esté cerrado y el SHA a etiquetar coincida con el HEAD aprobado de `main`.

La protección de tags debe vivir a nivel del repositorio. No se considera suficiente un control definido únicamente dentro de `.github/workflows/release-gate.yml`.

## 11. Rollback

Si el release falla:

1. Activa mantenimiento si el estado de datos es incierto.
2. Detén los servicios afectados.
3. Restaura el último backup PostgreSQL verificado en una base limpia/staging primero cuando sea posible.
4. Vuelve al tag/imagen anterior.
5. Levanta servicios.
6. Comprueba `/api/ready` y un flujo de venta controlado.
7. Documenta el incidente antes de reintentar el release.

Nunca uses SQLite/localStorage como mecanismo de rollback productivo.

## 12. Criterio de terminado

El proyecto puede marcarse como release productivo cuando:

- CI está verde;
- Release Gate manual está verde sobre el `main` aprobado;
- protección de `main` está activa;
- Tag ruleset de `v*` está activo con creación/actualización/eliminación restringidas;
- el Issue #38 está cerrado con los datos e infraestructura reales verificados;
- `.env.prod` real pasa validación;
- backup local existe y su checksum valida;
- copia off-site está confirmada por contenido;
- restauración de staging termina correctamente;
- dominio/HTTPS funcionan;
- login, venta, stock/IMEI, transferencia y permisos pasan smoke test;
- cualquier tag estable se crea únicamente sobre el HEAD aprobado de `main` después de cumplir todos los puntos anteriores.
