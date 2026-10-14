# Auditoría integral SoftMobile — informe consolidado parcial

**Dictamen provisional: no certificado para producción. Auditoría incompleta.** No se autoriza corregir todavía. El sistema responde y tiene CI aprobado, pero se encontraron defectos de integridad de stock, garantías, permisos, contratos de pago y recuperación. No recomendar operación irrestricta ni habilitar automatizaciones antes de resolver y validar estos bloqueos.

Línea base oficial `main`: **dba6763391d12c6c91c9904cba36725710f9280a**. Los archivos nuevos de auditoría no alteran esa línea base. La documentación se propone en el PR146 existente, sin fusionar.

## Cobertura real

- Inventario íntegro: **653archivos versionados**, sin exclusiones para inflar el porcentaje.
- Lectura semántica completa guardada: **471/653=72.13%**.
- Parcial: **11**. No revisado: **171**. Total pendiente de completar: **182**.
- Un archivo completo significa leído entero y razonado estáticamente, **no** todas sus ramas probadas ni integración/producción certificada. Los archivos vacíos/documentación también pertenecen al inventario; ponderación por número de archivos, no líneas ni criticidad.
- [COBERTURA.json](COBERTURA.json) registra path, blob exacto, estado y evidencia. [COBERTURA.md](COBERTURA.md) permite revisión visual. No reutilizar lectura si cambia blob sin cotejar diff.

## Estado por módulo

| Módulo | Evidencia y estado provisional |
|---|---|
| Backend API y negocio | Lectura integral de routers centrales y helpers; invariantes fallan en fixtures; pendientes de pruebas nuevas PostgreSQL |
| Stock, IMEI, reservas, transferencias | BUS01/02/05 reproducidos: reserva ajena consumida, recepción cero mueve seriales, retoma reasigna serial existente |
| Ventas, pagos, financiación | Contrato pagos mixtos incompatible FE01; reintentos sin idempotencia BUS07/FE02; auditoría posterior commit BUS10 |
| Garantías/posventa | BUS03/04 reproducidos: serial de producto ajeno aceptado, garantía serializada sin reemplazo; políticas monetarias no se cambiaron |
| Compras, proveedores, costos | Lectura estática central realizada; costo histórico existe; utilitarios y escenarios integrados pendientes; valoración mezcla moneda BUS09 |
| Usuarios, seguridad, sedes | Rutas canónicas y middleware revisados; exposición nested stock BUS06; permisos IA insuficientes SEC-AI01/02; JWT previo tras cambio contraseña AUTH01 |
| Reportes, cierres, contabilidad | Cálculos centrales inspeccionados; inconsistencias fecha/cache AN01/02 y moneda BUS09; falta conciliación extremo a extremo |
| Frontend, formularios, navegación | 61archivos leídos por bloque frontend más componentes UI y tests; faltan servicios grandes/componentes negocio restantes. Lint/build/49tests aprobados no cubren todos botones |
| Canales, IA y n8n | Legacy shadowing comprobado; CH005/006 y pérdida/duplicación de mensajes/fotos pendientes; IA false en runtime, Meta/n8n real no demostrado operativo |
| Base de datos/migraciones | Ledger propio y locking startup presentes; OPS04compatibilidad SQLite falla; OPS08truncate separado; conversión/restauración PostgreSQL real no probada aquí |
| Docker/deploy/backups/DR | Diferencia stack versionado vs VPS systemd; OPS01/02/03/05/06/07; offsite no configurado y provenance unknown |
| Tests/dependencias/Actions | CI exacto513backend/49frontend/4SQLite/1PG aprobado; brechas oráculos y alcance. Local9API+49frontend aprobados; browser y PG local bloqueados |
| Reparaciones/rehabilitación | No se demostró flujo completo para rehabilitar serial defectuoso; no asumir que cuarentena es reparación funcional |

## Hallazgos

**66entradas provisionales**:27HIGH,32MEDIUM,6LOW,1INFORMATIONAL. Ningún CRITICAL asignado en los archivos revisados; no implica ausencia en alcance pendiente. Las entradas incluyen riesgos de diseño y brechas de prueba/documentación, y algunas comparten causa raíz; no son66defectos independientes confirmados.

[HALLAZGOS.json](HALLAZGOS.json) y [HALLAZGOS.md](HALLAZGOS.md) enlazan los seis informes de bloque con ID, archivo/función/líneas, evidencia, impacto, escenario, recomendación y pruebas necesarias. Confirmación estática, reproducción lógica SQLite y verificación productiva son categorías diferentes.

Prioridades ya sustentadas: reservas/stock entre ventas y traslados; recepción cero IMEI; identidad de garantías/retomas; pagos mixtos e idempotencia; scope de sedes; respaldo y restauración fiables. Reconciliar FE02 con BUS07 como misma causa relacionada; CH005/UTIL07/DOC03 describen problemas n8n relacionados. CH002/003/004 de la auditoría previa quedan superados en handlers activos, no se cuentan abiertos nuevamente.

## Pruebas e infraestructura

[VERIFICACIONES.md](VERIFICACIONES.md) separa aprobadas, fallidas por reproducción, omitidas y bloqueadas, con SHA/jobs/comandos. Producción HTTP200 no demuestra integridad de negocio ni DR. El backend de disco coincide con main en144archivos app, pero dosfuentes frontend difieren y release header unknown; bundle real sigue pendiente.

## Plan y continuidad

[CONTINUIDAD.md](CONTINUIDAD.md) lista los182archivos a continuar, orden técnico y plan de corrección por dependencias. La revisión paralela alcanzó límite real de uso durante ampliación; sólo lo guardado con evidencia cuenta. No hay auditoría ejecutándose después del turno.

Antes de la fase correctiva: completar182archivos, cotejar relaciones y falsos positivos, reproducir invariantes relevantes en PostgreSQL16 descartable, completar E2E/browser y presentar plan final. **Esperar autorización de usuario para corregir**.

## Condiciones para cierre100%

1. Inventario actualizado y todos archivos relevantes revisados íntegros, sin parcial/pendiente; dictamen con causas raíz depurado.
2. Hallazgos críticos/altos corregidos mediante PR autorizados y regresiones negativas/concurrencia PostgreSQL; medio/bajo resuelto o aceptado explícitamente con justificación.
3. Pagos/totales/stock/IMEI/transferencias/garantías/costos/auditoría conciliados de extremo a extremo y pruebas de fallo/reintento sin efectos parciales.
4. CI final, seguridad dependencias/contenedores, browser crítico y staging operativo aprobados sin omisiones camufladas.
5. GitHub como fuente única, main protegido, tagsv* protegidos, checkout/artefacto limpio y SHA de runtime verificable; cero diffs productivos sin versionar.
6. Configuración real valida; respaldo local íntegro, copia offhost validada por contenido, DR en staging con RPO/RTO del proceso completo y rollback demostrado.
7. HTTPS/readiness/observabilidad/alertas comprobados; permisos por rol/sede negativos, uso simultáneo y caída API fail-closed.
8. Cada integración incluida requiere credenciales/configuración y flujo real entrada→respuesta→reintento; IA deshabilitada es válida sólo si se excluye expresamente del alcance certificado.
9. Reportar por separado implementado, probado, integrado, desplegado y verificado en producción; no declarar100% sólo por CI o compilación.


## Checkpoint posterior: continuación 02

La cifra vigente sustituye el checkpoint anterior: 552/653 (84.53%) de lectura completa; 101 pendientes/parciales. Evidencia: CONTINUACION_02.json y REPRO_CONTINUACION_02.json. La auditoría sigue incompleta. FE-01 rectificado: backend rechaza desglose inconsistente, no se confirmó persistencia corrupta. Nuevos riesgos y fallos no equivalen a verificación de producción.
