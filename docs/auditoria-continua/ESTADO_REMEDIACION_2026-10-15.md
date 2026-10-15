# Auditoría SoftMobile — estado de remediación y verificación

**Fecha:** 15 de octubre de 2026  
**Alcance:** ERP `sistema-de-inve-sand`, auditoría PR #146, registro fijo de 110 entradas.  
**Precaución:** este documento es evidencia y planificación técnica, **no autorización para desplegar**.

## Contabilidad verificable de intervenciones

- Base de auditoría estática: **110 hallazgos provisionales** (34 HIGH, 63 MEDIUM, 12 LOW, 1 informativo).
- PR de integración #152: **76 entradas intervenidas con correcciones, pruebas o mitigaciones parciales** (incluye T05, FE-13 y CONT03-NS-01 añadidos en esta ronda).
- **34 entradas sin intervención de código acreditada** a esta fecha. Las 76 intervenciones no equivalen a 76 incidencias cerradas en producción.
- **Dos bloqueos HIGH operativos:** PROD-01 (provenance/código real desplegado) y PROD-02 (destino de backup remoto verificable).
- La idempotencia general BUS-07, las operaciones multi-fila FE-04 y los flujos de IA aún requieren validación funcional y pueden necesitar nuevas correcciones.

## Verificación de lectura del servidor autorizado (sin cambios)

La inspección fue exclusivamente de metadatos y nombres de ficheros, **sin leer secretos**, mutar ficheros, reiniciar servicios, lanzar backups ni cambiar la aplicación.

1. El ERP activo se ejecuta en **systemd** (`inventario.service`) con directorio de trabajo `/var/www/inventario/backend`; sirve API FastAPI por loopback. Nginx sirve el frontend desde `/var/www/inventario/dist`. **No atribuir el despliegue ERP a los contenedores de Chatwoot**.
2. Hay múltiples árboles de release/código, incluidos `/opt/inventario-staging`, `/opt/inventario-release`, `/opt/inventario-brand-release` y `/var/www/inventario`. Los commits/ramas no corresponden a la línea base `main` auditada. El árbol de staging tenía **8 ficheros versionados modificados** en el momento de la lectura. El frontend `App.tsx` del directorio servido presenta checksum diferente al del árbol release, aunque la entrada backend `main.py` coincidía entre directorios. **PROD-01: diferencia de procedencia confirmada; no corregida.** No inferir que el código que se está auditando corresponde al binario que atiende clientes.
3. En el entorno operativo inspeccionado, la política de respaldo remoto consta como **obligatoria**, pero **no se halló destino remoto configurado** en el archivo de entorno del backend. Las utilidades `rclone`, `restic` y `aws` no estaban instaladas en la ruta de comandos y no se observó el servicio offsite del ERP ejecutándose en Docker. Se detectó un cron con nombre relacionado con backups, sin verificar su contenido/destino; **es posible que existan otros respaldos independientes no inspeccionados**. **PROD-02: capacidad offsite no acreditada; no corregida**.
4. Dado este estado, un gate verde de GitHub **no prueba** la instalación real. Es indispensable inventariar cómo se construyó frontend/backend, comprobar artefactos y secrets con personal autorizado, y planificar rollout/rollback sobre copia o staging sin tocar producción.

## Cambios de esta ronda en rama de integración

- Autenticación de solicitudes de fotos: rechazo de Bearer inválido y de secreto de integración ausente; nueva prueba de autorización productiva.
- T05: cada E2E destructivo PostgreSQL utiliza un esquema propio descartable, con rechazo de DB remota/productiva y prueba de aislamiento.
- FE-13: margen bruto incorpora el costo histórico real de regalías; historiales y gráficas financieras usan fecha de venta efectiva (no fecha de borrador), con pruebas de meses y regalos.
- CONT03-NS-01: configuración técnica de canales toma WhatsApp/Messenger/Instagram del perfil técnico seleccionado, no del formulario previo.

## Criterios de salida obligatorios

1. Todos los checks del **último SHA** de la rama de integración deben aprobar, incluyendo backend PostgreSQL, E2E, navegador, lint y seguridad. Ante cualquier error, bloquear merge/despliegue.
2. Comprobar E2E por sede/roles, reintentos idempotentes, flujos Meta/n8n, garantías IMEI, venta con descuentos/financiamiento y devoluciones con datos **sintéticos**.
3. Conciliar la versión real del servidor y frontend contra un commit aprobado; tratar las diferencias manuales como cambios que deben rescatarse antes de actualizar.
4. Configurar y verificar respaldo remoto offsite mediante restore aislado reciente; sin evidencia de recuperación, **no aprobar producción**.
5. La fusión del PR o el despliegue del VPS requieren decisiones explícitas distintas y respaldos comprobados; **este PR permanece en borrador**.
