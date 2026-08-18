# Deploy Checklist

Procedimiento corto. Para explicación completa usa [`docs/PRODUCCION_FINAL.md`](docs/PRODUCCION_FINAL.md).

## 1. Preparar

```bash
APP_DOMAIN=inventario.tudominio.com ./deploy/prepare-prod-env.sh
```

Completa `deploy/.env.prod`, especialmente:

- dominio/hosts/CORS;
- secretos generados;
- `BACKUP_RCLONE_DESTINATION`;
- `RCLONE_CONFIG_*` del proveedor off-site;
- integraciones opcionales que realmente se usarán.

## 2. Validar

```bash
./deploy/validate-prod.sh ./deploy/.env.prod
```

Debe terminar con `Validación de producción OK.`

## 3. Levantar

```bash
cd deploy

docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  --profile backup \
  --profile backup-offsite \
  up -d --build
```

Con monitoreo:

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  --profile backup \
  --profile backup-offsite \
  --profile monitoring \
  up -d --build
```

## 4. Verificar

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
curl -fsS https://inventario.tudominio.com/api/ready
curl -fsS https://inventario.tudominio.com/api/health
```

Después realiza un smoke test controlado de login, inventario, venta/IMEI, transferencia, cierre diario y permisos.

## 5. Confirmar backups

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=100 backup
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=100 backup-offsite
```

Confirma:

- `.sql.gz` reciente;
- `.sha256` correspondiente;
- copia visible en el destino remoto;
- restauración de staging/DR drill exitosa antes de un release importante.

## Rollback

Si el release introduce un problema:

1. Evita nuevas escrituras si la integridad de datos es incierta.
2. Detén la versión afectada.
3. Restaura el backup PostgreSQL verificado cuando el problema involucre datos.
4. Despliega el tag/imagen anterior.
5. Comprueba `/api/ready` y flujos críticos.
6. No uses localStorage/SQLite como fallback productivo.

## Regla de release

El tag estable se crea **después** de fusionar el PR validado a `main`. No etiquetes directamente una rama de trabajo.
