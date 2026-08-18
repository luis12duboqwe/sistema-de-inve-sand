# Auditoría Técnica Final del Sistema

Fecha: **18 de agosto de 2026**  
Repositorio: `luis12duboqwe/sistema-de-inve-sand`  
PR de cierre: **#37 — `agent/finalize-production` → `main`**

## 1. Alcance

Esta auditoría sustituye los informes históricos que describían el proyecto como dual-mode listo para producción con tareas de limpieza menores. El sistema cambió de forma sustancial desde entonces: se endurecieron PostgreSQL, CI, concurrencia, seguridad de operaciones, backups, contenedores y el proceso de release.

La revisión final cubre arquitectura de ejecución, integridad de datos, migraciones, recuperación, seguridad de dependencias/contenedores, documentación y gobierno del release.

## 2. Hallazgo crítico: fallback local en producción

### Riesgo

El frontend podía arrancar con `settings_use_api=false` mientras cargaba preferencias y la capa unificada conservaba un servicio local. Una configuración antigua o un error podía provocar operación contra almacenamiento del navegador en lugar del backend productivo.

### Corrección

Se añadió una política central en `src/lib/runtimePolicy.ts` y se integró con `kvStorage` y `useKV`:

- en producción `settings_use_api` se resuelve como `true` desde el primer render;
- guardar `false` en producción se normaliza a `true`;
- borrar la preferencia no habilita modo local;
- errores de lectura KV tampoco degradan a local;
- desarrollo/pruebas conservan el modo local.

`BackendConnectionCheck` también fue endurecido:

- producción prueba únicamente la URL configurada y same-origin `/api`;
- no prueba `localhost` del navegador del usuario;
- no ofrece bypass para continuar sin backend;
- una caída del servidor bloquea la operación y permite reintentar.

Se añadieron pruebas unitarias específicas de la política runtime.

**Resultado:** la producción ya no usa el almacenamiento local como mecanismo silencioso de continuidad o rollback.

## 3. Migraciones de base de datos

### Estado anterior

Existían ajustes automáticos idempotentes, pero sin un ledger versionado de migraciones aplicadas.

### Corrección

`backend/app/utils/auto_migrations.py` ahora:

- crea `schema_migrations`;
- define IDs inmutables y ordenados;
- ejecuta sólo migraciones pendientes;
- registra cada migración completada;
- valida tablas/columnas críticas al finalizar;
- detiene el arranque ante error.

Se añadió `backend/tests/test_auto_migrations.py` para probar registro e idempotencia sobre PostgreSQL, y `backend/conftest.py` limpia el ledger entre tests para evitar contaminación.

**Resultado:** una instalación existente puede converger de forma rastreable y el backend no opera con un esquema parcialmente actualizado.

## 4. Backup y recuperación

El flujo local existente ya generaba `pg_dump`, compresión gzip, validación, tamaño mínimo y SHA-256. Se añadió el segundo nivel requerido para continuidad real:

- servicio `backup-offsite` en Docker Compose;
- imagen rclone;
- volumen de backups montado sólo lectura;
- réplica de `.sql.gz` y `.sha256` por checksum;
- destino configurable mediante `BACKUP_RCLONE_DESTINATION`;
- soporte de credenciales mediante `RCLONE_CONFIG_*` en el entorno/secret manager;
- validación del perfil off-site en `deploy/validate-prod.sh` y `release-gate.yml`.

El repositorio ya incluye `deploy/dr-drill.sh` y un workflow semanal de DR para staging.

**Pendiente externo:** destino/credenciales reales y ejecución confirmada del DR drill. Se rastrea en Issue #38.

## 5. Seguridad de dependencias y contenedores

La política de CI no fue debilitada. Durante el PR #37 los gates detectaron problemas reales y se corrigieron en origen.

### npm / filesystem

`npm audit` y Trivy detectaron `nanoid 3.3.17` con severidad HIGH. El lockfile se regeneró de forma reproducible y quedó en `nanoid 3.3.18`, sin introducir un cambio mayor del frontend ni excepciones al scanner.

### Imagen backend

El scanner de imagen detectó paquetes base Debian de la familia `util-linux` con una corrección publicada que aún no estaba instalada en el runtime. El Dockerfile ahora ejecuta `apt-get upgrade` después de actualizar índices y antes de instalar dependencias runtime.

**Regla:** el HEAD final debe demostrar que filesystem e imágenes están limpios según la política HIGH/CRITICAL vigente antes de fusionar.

## 6. CI y pruebas

La matriz automatizada vigente incluye:

- ESLint;
- frontend tests con coverage;
- build del frontend;
- backend sobre PostgreSQL real;
- E2E de runtime y negocio;
- E2E PostgreSQL con prueba de concurrencia de stock/IMEI;
- auditoría de dependencias npm/Python;
- Trivy de filesystem;
- build y Trivy de imágenes backend/frontend.

`release-gate.yml` repite calidad/seguridad y valida una configuración productiva sintética, incluido el perfil off-site.

El estado exacto del último HEAD debe consultarse en los checks del PR #37. Este documento no sustituye el gate automatizado ni autoriza una fusión con checks pendientes/fallidos.

## 7. Documentación

Se eliminó la contradicción principal entre guías antiguas y la arquitectura actual:

- `README.md` ya no afirma que el sistema esté finalizado basándose en 24 tests antiguos;
- `COMIENZA_AQUI.md` usa el flujo actual;
- `CHECKLIST_PRODUCCION.md` refleja CI/API-only/off-site/DR;
- `DEPLOY_CHECKLIST.md` refleja Docker Compose y rollback actual;
- `docs/PRODUCCION_COMPLETA.md` apunta al runbook vigente;
- `docs/PRODUCCION_FINAL.md` es la fuente canónica para producción.

## 8. Limpieza

Se retiraron artefactos que no pertenecen al código fuente:

- `.coverage` versionado;
- archivo vacío `backend/assert`;
- bytecode `.pyc` bajo `__pycache__`.

No se eliminaron scripts históricos de forma masiva sólo por su nombre; cualquier limpieza adicional debe basarse en evidencia de que no participan en operación, migración o soporte.

## 9. Gobierno de `main`

El repositorio tenía `main` sin protección al iniciar esta fase. El conector disponible no expone una acción para crear Branch Protection/Rulesets, por lo que no se simuló ni se afirmó que esa configuración exista.

Issue #38 exige:

- PR obligatorio;
- checks obligatorios;
- bloqueo de force-push;
- bloqueo de eliminación;
- selección de nombres de checks reales después de estabilizar el PR.

## 10. Riesgos residuales y acciones externas

No son defectos que deban resolverse escribiendo secretos en Git:

1. Configurar protección real de `main`.
2. Configurar un remote off-site y sus credenciales reales.
3. Configurar secretos de staging para DR.
4. Ejecutar una restauración real y verificarla.
5. Ejecutar smoke tests sobre dominio/HTTPS e infraestructura productiva real.

## 11. Conclusión

La arquitectura de código queda orientada a una operación productiva segura: API-only en producción, PostgreSQL, migraciones rastreables, CI estricto, backup local + off-site, DR y documentación canónica.

**Clasificación de cierre:** `CANDIDATO A PRODUCCIÓN` hasta que el CI del HEAD final del PR #37 esté completamente verde y el Issue #38 sea completado.

No se debe crear el tag estable ni declarar el proyecto desplegado al 100% antes de cumplir ambos requisitos.
