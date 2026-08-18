# Auditoría Final — Resumen Ejecutivo

Fecha de revisión: **18 de agosto de 2026**  
Rama revisada: `agent/finalize-production`  
PR: **#37**

## Estado

**Código: candidato a producción, condicionado a CI final y prerrequisitos externos.**

La auditoría anterior de mayo de 2026 quedó obsoleta. Esta revisión incorpora el endurecimiento del PR #36 y la fase final del PR #37.

## Cambios de cierre implementados

- Producción fuerza API desde el primer render; el modo local queda sólo para desarrollo/pruebas.
- La pantalla productiva no permite continuar si el backend está caído.
- Migraciones PostgreSQL de compatibilidad quedan versionadas en `schema_migrations`, son idempotentes y fail-fast.
- Backups PostgreSQL conservan compresión/checksum y pueden replicarse fuera del host mediante `backup-offsite` + rclone.
- El release gate valida el perfil off-site de forma sintética.
- Documentación productiva consolidada en `docs/PRODUCCION_FINAL.md`.
- `nanoid` se actualizó de 3.3.17 a 3.3.18 después de que CI detectara una vulnerabilidad HIGH; no se redujo la severidad del gate.
- El runtime backend actualiza paquetes Debian antes de empaquetar la imagen para incorporar correcciones de seguridad publicadas.
- Artefactos generados/accidentales se eliminan del repositorio (`.coverage`, `backend/assert`, `.pyc`).

## Validación automatizada

El CI del PR es la fuente de verdad para el HEAD final y debe quedar completamente verde antes de fusionar. La matriz incluye:

- lint;
- pruebas/coverage frontend;
- build frontend;
- backend sobre PostgreSQL;
- E2E de runtime y negocio;
- E2E PostgreSQL con concurrencia de stock/IMEI;
- auditoría npm y Python;
- Trivy de filesystem e imágenes.

Durante esta auditoría los gates detectaron y obligaron a corregir dos problemas reales de seguridad: `nanoid 3.3.17` y paquetes Debian del runtime backend. Ninguno fue silenciado ni exceptuado.

## Prerrequisitos fuera del código

El Issue **#38** concentra las acciones que requieren configuración real del entorno/GitHub:

1. Proteger `main` con PR + checks obligatorios y bloqueo de force-push/eliminación.
2. Configurar `BACKUP_RCLONE_DESTINATION` y credenciales `RCLONE_CONFIG_*` reales fuera del repositorio.
3. Configurar secretos de staging y ejecutar/verificar `DR Drill (Staging)`.

Mientras el Issue #38 permanezca abierto, el sistema no debe declararse desplegado o cerrado al 100% en producción.

## Criterio de aprobación

Aprobar el release únicamente cuando:

- CI del HEAD final del PR #37 esté verde;
- PR #37 se fusione a `main` sin saltarse gates;
- `main` esté protegida;
- `deploy/.env.prod` real pase `deploy/validate-prod.sh`;
- exista copia local y off-site verificada;
- una restauración/DR drill de staging haya terminado correctamente;
- smoke tests de login, permisos, inventario, venta/IMEI, transferencia y cierre diario pasen.

Para operación y despliegue, usar `docs/PRODUCCION_FINAL.md` como fuente canónica.
