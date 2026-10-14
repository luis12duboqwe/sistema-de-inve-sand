# Pruebas y comprobaciones — 2026-10-14

Línea base: `dba6763391d12c6c91c9904cba36725710f9280a` (`main`). No se modificó código ejecutable, ni se fusionaron PR, ni se desplegó, ni se cambió información del negocio.

## GitHub verificado

- PR abiertos al inicio: #147 corrección WhatsApp (draft, sin fusionar); #146 documentación de auditoría; #144 Dependabot (33 updates, sin fusionar). El cambio #147 afecta una función legacy retirada por `integrity_overrides`; el handler activo ya usa Facebook Graph. No asumir que este PR remedia un defecto operacional vigente.
- [CI del SHA](https://github.com/luis12duboqwe/sistema-de-inve-sand/actions/runs/38613017733): siete jobs aprobados. Logs consultados, no sólo insignia verde.
- Backend PostgreSQL 16: **513 passed**, 1 warning, **71%** cobertura, job116020907735.
- Frontend: **21 archivos / 49 passed**; statements18.9%, branches16.22%, functions15.43%, lines19.89%; job116020907878. Cobertura de pruebas distinta de cobertura semántica de auditoría.
- Runtime y negocio SQLite E2E: **4 passed**, job116020907516.
- PostgreSQL E2E: **1 passed**, job116020907803. Sus asserts insuficientes se documentan en T01; aprobación no prueba todos los escenarios concurrentes.
- [Release Gate](https://github.com/luis12duboqwe/sistema-de-inve-sand/actions/runs/38613017711): aprobado. Es gate automatizado, no certificación de configuración real.
- Ruleset21015275 de main activo: PR requerido, siete checks estrictos, sin bypass, bloquea force-push/borrado. API rulesets sólo devolvió este ruleset; falta protección tags v*. Lectura branch-protection403 por permisos conector; ruleset independiente sí leído completo.
- Issue38 abierto: se recuperaron cuerpo y once comentarios, incluido DR aislado reportado 2026-10-07. Se conserva como evidencia histórica reportada; no se volvió a restaurar producción ni se infiere respaldo externo configurado.

## Ejecuciones locales frescas

| Comando | Resultado | Límite |
|---|---|---|
| `npm ci --legacy-peer-deps --ignore-scripts` | Instalación aprobada; sin modificar lockfile | Primer intento offline falló ENOTCACHED; alternativa online funcionó |
| `npm run lint` | Exit0 | No demuestra lógica negocio |
| `npm run test:coverage` | Exit0;49passed,21archivos | 19.89%líneas; mocks, no browser |
| `npm run build` | Exit0 | No despliegue |
| `pytest -q tests/test_health_endpoints.py tests/e2e/test_runtime_e2e.py tests/e2e/test_business_flows_e2e.py` | Exit0;9passed,3warnings | Python3.12, SQLite temporal; no PostgreSQL |
| Cinco suites shell deploy | Todas exit0 | Fixtures/mocks; lista y stdout en BLOQUE_deploy.json |
| Reproducciones BUS01/02/03/04/05/06 | Fallos de lógica observados con fixtures SQLite aisladas | No demuestran concurrencia ni comportamiento PostgreSQL; detalles BLOQUE_business |
| Backup fallido pg_dump sintético | Script exit0, SQL descomprimido0bytes, sidecar, SUCCESS | Defecto GitHub OPS03; no se ejecutó backup real |
| Migración precios SQLite sintética | ProgrammingError binding Decimal | Defecto OPS04; no se migraron datos reales |
| Calendar/Progress SSR | Defectos semánticos reproducidos | No prueba visual navegador, detalles BLOQUE_utilities |

Pruebas fallidas de producto: reproducciones anteriores detectan defectos; las suites disponibles enumeradas arriba aprobaron. Pruebas omitidas históricas del VPS: informe previo declaraba474SKIPPED,0ejecutadas, no aprobación. Las nuevas reproducciones carecen de regresiones PostgreSQL aún: PENDIENTE.

No ejecutadas localmente: suite completa backend PostgreSQL y E2E PostgreSQL (servidor/Docker no disponibles; instalación local no completó por restricciones de entorno/repositorios), E2E browser (descarga Chromium fallida). No se sustituyeron PostgreSQL por SQLite para certificar producción. Consulta adicional de colección workflow browser fue rechazada por allowlist del conector: no se infiere resultado.

## Runtime real, sólo lectura

- `https://invjear.com/api/health` y `/api/ready`: HTTP200, PostgreSQL conectado, ambiente production, IA false, email sin configurar; `X-Release-SHA: unknown`.
- Servicio real `inventario.service`, Uvicorn cuatro workers, código bajo `/var/www/inventario/backend`. No es stack Docker Compose; diferencias OPS01/02 de Compose se clasifican sobre arquitectura versionada, no se afirman reproducidas en este servicio.
- Checkout `/var/www/inventario`: SHA1cfa35e9ba2e1db28e43285fac482d18021426ef; cambios locales backend/backup_database.sh,src/App.tsx,src/components/AIStatusWidget.tsx,tests/browser/receipt.spec.ts. No se sobrescribieron. La modificación backup no se evaluó íntegra en runtime: OPS03 confirmado en GitHub, su presencia efectiva en host queda pendiente.
- Comparación exacta de348blobs backend/app+src contra GitHub auditado:346coinciden,ninguno ausente,2distintos (`src/App.tsx`, `src/components/AIStatusWidget.tsx`). Todos144archivos backend/app coinciden. Esto no prueba bundle servido ni revisión del código ejecutado en memoria.
- `.env` real comprobado sólo por presencia/booleanos: APP_BUILD_SHA ausente, REQUIRE_OFFSITE_BACKUP=true, destino offsite no configurado, IA false, secreto Meta no presente. Ningún valor secreto publicado.
- `/api/metrics` público HTTP200 en VPS systemd. Compose lo bloquea con404: conservar diferencia explícita; revisar exposición real con política de seguridad.

## Evidencia previa recuperada

PR146 contiene CANALES_2026-10-14.md; CH002/003/004 legacy superados por handlers activos/middleware. CH001 parcialmente superado para webhook, persiste en camino IA y limpieza compartida; CH005/006vigentes. Ver BLOQUE_security-ai.json. Informes VPS no rastreados ESTADO_Y_PLAN/INVENTARIO_ARCHIVOS/RESUMEN_AUTOMATICO fueron leídos como contexto: enumerar535archivos y comprobar sintaxis no equivalía a revisión completa. Esta cobertura usa blobs de GitHub, sin importar aquel porcentaje como semántico.


## Continuación03 — estado vigente

653/653 revisión estática completa (652texto,1lock estructural), todos blobs exactos. HMAC12assertions aprobadas200/401 esperado; eventos vacíos/NoDB. npm audit exit0,0advisories conocidos. Browser cloud público: /catalogo falla fetch y sin tarjetas; API público200/189items; / llega a login. Sin autenticación, mensajes ni escrituras. PG alternativa pgserver16.2 instalada solo scratch, no inicia por useradd/setgroups, suite local no ejecutada. VERIFICACIONES_CONT03.json y INFORME_INTEGRAL.md detallan alcance y limitaciones.
