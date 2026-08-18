# Checklist de Producción

Fuente canónica complementaria: [`docs/PRODUCCION_FINAL.md`](docs/PRODUCCION_FINAL.md).

## Código y CI

- [ ] PR final parte del `main` vigente.
- [ ] Lint frontend en verde.
- [ ] Tests frontend/coverage en verde.
- [ ] Build frontend en verde.
- [ ] Backend tests sobre PostgreSQL en verde.
- [ ] E2E runtime/negocio/PostgreSQL en verde.
- [ ] Auditoría npm/Python sin vulnerabilidades bloqueantes.
- [ ] Trivy sin hallazgos HIGH/CRITICAL bloqueantes según política vigente.
- [ ] Release Gate en verde.

## Política de datos

- [ ] Build de producción fuerza `settings_use_api=true` desde el primer render.
- [ ] No existe bypass productivo para continuar sin backend.
- [ ] El frontend productivo no prueba `localhost` del usuario como backend.
- [ ] Una caída de API produce error/bloqueo, no escritura local silenciosa.

## Base de datos

- [ ] `DATABASE_URL` usa PostgreSQL.
- [ ] `schema_migrations` existe después del arranque.
- [ ] Migraciones pendientes se aplican sin error.
- [ ] `/api/ready` confirma base de datos disponible.
- [ ] Se comprobó un flujo de venta y stock/IMEI sobre PostgreSQL real.

## Seguridad

- [ ] `ENVIRONMENT=production`.
- [ ] `DEBUG=false`.
- [ ] `SECRET_KEY` fuerte y exclusivo.
- [ ] `CHANNEL_ENCRYPTION_KEY` fuerte y exclusivo.
- [ ] `SETUP_TOKEN` fuerte y no publicado.
- [ ] `ENABLE_DESTRUCTIVE_PURGE=false` salvo operación excepcional controlada.
- [ ] `DESTRUCTIVE_OPERATION_TOKEN` separado del resto de secretos.
- [ ] `CORS_ORIGINS` restringido.
- [ ] `ALLOWED_HOSTS` restringido.
- [ ] Credenciales y `.env.prod` fuera de Git.

## Backups y continuidad

- [ ] Servicio `backup` activo.
- [ ] Backup `.sql.gz` reciente existe.
- [ ] Checksum `.sha256` valida.
- [ ] `REQUIRE_OFFSITE_BACKUP=true`.
- [ ] `BACKUP_RCLONE_DESTINATION` apunta fuera del host.
- [ ] Servicio `backup-offsite` replica correctamente.
- [ ] Se verificó presencia de una copia remota reciente.
- [ ] DR drill/restauración de staging completado exitosamente.

## Infraestructura

- [ ] `./deploy/validate-prod.sh ./deploy/.env.prod` termina OK.
- [ ] HTTPS y dominio funcionan.
- [ ] Backend healthcheck pasa.
- [ ] Frontend carga desde el dominio productivo.
- [ ] Logs estructurados disponibles.
- [ ] Monitoreo/alertas configurados según la operación.

## Smoke test de negocio

- [ ] Login y logout.
- [ ] Roles/permisos.
- [ ] Restricción por ubicación.
- [ ] Crear/editar producto.
- [ ] Stock por ubicación.
- [ ] Registrar IMEI y consultar historial.
- [ ] Crear venta y descontar stock/IMEI.
- [ ] Cancelar/revertir flujo permitido.
- [ ] Transferencia entre tiendas.
- [ ] Recepción con incidencias/cantidades.
- [ ] Compra/recepción de proveedor.
- [ ] Devolución/garantía.
- [ ] Cierre diario y código de validación.
- [ ] Reportes críticos.
- [ ] Auditoría registra operaciones sensibles.

## Gobierno de GitHub

- [ ] `main` requiere pull request.
- [ ] Checks obligatorios seleccionados.
- [ ] Force push bloqueado.
- [ ] Eliminación de `main` bloqueada.

## Cierre

- [ ] PR marcado listo para revisión sólo después de checks verdes.
- [ ] PR fusionado sin saltarse gates.
- [ ] Release/tag creado desde `main` fusionado, no desde una rama de trabajo.
- [ ] Release Gate ejecutado para el tag.
- [ ] Primer backup post-release confirmado local y off-site.
