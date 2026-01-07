# Operación y Observabilidad

Guía práctica para operar el backend en producción con logging estructurado,
manipulación homogénea de errores y opciones de monitoreo/APM ligero.

## Logging estructurado
- El backend usa `setup_logging()` con formateador JSON por defecto cuando
  `ENVIRONMENT=production` o `LOG_STRUCTURED=true`.
- Variables relevantes (todas opcionales):
  - `LOG_LEVEL` (`INFO` por defecto)
  - `LOG_STRUCTURED` (`true`/`false`)
  - `LOG_TO_FILES` (habilita `logs/app.log` y `logs/errors.log` rotativos)
  - `LOG_DIRECTORY` (destino para archivos)
  - `LOG_INCLUDE_CONSOLE` (útil en contenedores sin filesystem persistente)
- Los logs incluyen `request_id`, `user_id` (cuando se propaga) y contexto del módulo
  que originó la traza; esto facilita enviarlos a Loki, CloudWatch o ELK.

## Correlación de requests
- El middleware `RequestContextMiddleware` inyecta `X-Request-ID` si el cliente no
  lo envía. Ese valor se replica en la respuesta y se agrega al contexto de logging.
- Para rastrear una llamada basta con buscar el mismo `request_id` en los logs.

## Manejo homogéneo de errores
- Todas las excepciones no controladas pasan por `global_exception_handler`, que
  responde con `HTTP 500` y mensaje genérico sin exponer stack traces.
- Las `HTTPException` explícitas mantienen el código/mensaje definido por cada
  router, pero igualmente quedan registradas en el log (nivel `warning`/`error`).
- Recomendación: al crear nuevos endpoints reutilizar helpers existentes para
  mensajes (`detail`) y documentar errores esperados en los esquemas de respuesta.

## Integración opcional con Sentry
1. Añadir las variables en el entorno de producción:
   ```env
   SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
   SENTRY_ENVIRONMENT=production
   SENTRY_TRACES_SAMPLE_RATE=0.1   # 10% de las transacciones
   SENTRY_PROFILES_SAMPLE_RATE=0.0 # activar solo si se necesita perf profiling
   ```
2. Reiniciar el backend; `initialize_observability()` configura Sentry con las
   integraciones de FastAPI, logging y SQLAlchemy.
3. Verificar en Sentry que:
   - Se reciben eventos de error cuando se provoca un `500` controlado.
   - Las transacciones incluyen el nombre del endpoint gracias a
     `FastApiIntegration(transaction_style="endpoint")`.

## Monitoreo sugerido
- **Healthcheck:** `/api/health` ya expone estado de API y DB; ideal conectarlo a
  un load balancer o monitor externo (p.ej. UptimeRobot).
- **APScheduler:** si `ENABLE_FORECAST_SCHEDULER` está activo, conviene monitorear
  el proceso mediante logs y alertas sobre fallas consecutivas.
- **Alertas:** configurar triggers sobre palabras clave (`success=false` en logs
  críticos) o usar Sentry para notificar por Slack/Email.
- **Retención:** exportar `logs/errors.log` a almacenamiento externo (S3, Blob) al
  final de cada día para conservar histórico de 30 días.

Con estos elementos queda cubierto el frente de monitoreo/observabilidad descrito
en `docs/EXECUCION_PARALELA_PLAN.md` sin introducir dependencias obligatorias.
