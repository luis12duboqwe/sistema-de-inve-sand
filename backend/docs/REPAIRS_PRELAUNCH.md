# Módulo de reparaciones — piloto previo a producción

**Estado:** desarrollado y validado en entorno aislado, **no instalado ni activado en el VPS productivo**. WhatsApp permanece fuera del alcance.

## Código (solo en esta rama)
- `backend/app/models/repairs.py`: `RepairCase` y `RepairEvent`, evento append-only con claves únicas, revisión optimista, sucursal, técnico y estado. No almacena teléfono, IMEI ni información bancaria.
- `backend/app/schemas/repairs.py`: validación estricta; rechaza campos no definidos, números de cuenta, teléfono, IMEI y datos bancarios.
- `backend/app/services/repairs_policy.py`: transiciones recibida→diagnóstico→presupuesto→aprobación→reparación→QA→entrega, con aprobación humana y confirmación de repuestos obligatorias.
- `backend/app/routers/repairs.py`: API de creación, listado, detalle, historial y asignación de técnico. Solo usuarios superadministradores, con bandera `SOFTMOBILE_REPAIRS_ENABLED=true`.
- `backend/app/main.py`: importa y registra las rutas **únicamente si** `SOFTMOBILE_REPAIRS_ENABLED=true`; por defecto no existen rutas ni DDL para esta funcionalidad.

## Validación técnica hecha
En el VPS se probó una copia del código en un FastAPI aislado con SQLite de memoria y la virtualenv del backend, sin importar `app.main` ni alterar la base PostgreSQL de inventario. **15/15 tests HTTP aprobados**:
- Sin activar la bandera: 503; sin autenticación: 401/403.
- Solo sucursales activas y categorías válidas; bloquea campos personales añadidos.
- Ciclo de diagnóstico, presupuesto, aprobación, reparación, QA y entrega.
- Asignación exclusiva a usuarios activos con rol Técnico; rechazo de otro rol.
- Control de revisión, eventos idempotentes y bitácora sin mensajes a clientes.

## Antes de instalar o activar en producción
1. Revisar migración PostgreSQL para tablas `repair_cases`/`repair_events`, restricciones, índices, políticas de retención, backup y rollback. No aplicar `create_all` a ciegas sobre producción.
2. Validar roles y permisos de empleados y sucursales; por defecto solo superadministradores. Agregar separación entre técnicos y gerentes, con pruebas por sucursal.
3. Construir interfaz de taller y asignación, repuestos y costos, garantías y recepción/entrega documental.
4. Determinar evidencia verificable del consentimiento y aprobación del cliente: el número de referencia cargado por el administrador **no prueba por sí solo** la autorización del cliente.
5. Hacer integración real en base aislada con PostgreSQL, auditoría de seguridad y aceptación del propietario antes de habilitar la bandera.
6. No activar notificaciones automáticas de WhatsApp ni cobros. Esas integraciones quedan para otras fases.

La API en borrador no habilita pública o automáticamente ninguna operación comercial.