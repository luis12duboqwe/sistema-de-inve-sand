# Plan de Refactorización y Consola RBAC

## Objetivos
1. Separar los modelos y esquemas enormes en módulos coherentes sin romper compatibilidad.
2. Entregar una consola UI que permita gestionar usuarios y roles usando los endpoints existentes (`auth_router`).
3. Mantener la dualidad Local/API al exponer la consola solo en modo API y respetar permisos (`check_permission`).

## Fase A – Refactor de Naming y Módulos

### 1. Estructura propuesta (backend/app)
```
models/
  __init__.py           # reexporta clases para compatibilidad
  base.py               # mixins, timestamps
  product.py            # Product, Stock, IMEI
  order.py              # Order, OrderItem, TradeIn
  location.py           # Location, SalesProfile, StockTransfer
  user.py               # User, Role, Permission
schemas/
  __init__.py           # mantiene importaciones actuales
  product.py
  order.py
  rbac.py
```

### 2. Pasos
1. **Preparar módulos**: mover clases respetando import order. Añadir comentarios `# FIXME: legacy` donde aún existan campos V1.
2. **Actualizar importaciones**: buscar `from app import models` y reemplazar por rutas nuevas (`from app.models import order as order_models`). Añadir reexports en `models/__init__.py` para permitir migración gradual.
3. **Naming consistente**: asegurar snake_case en DB y camelCase en TS. Documentar mapeo en este archivo para QA.
4. **Tests manuales**: ejecutar `python backend/check_production_readiness.py` y pruebas CRUD básicas (`orders`, `stock_transfers`).

### 3. Riesgos y mitigaciones
- *Circular imports*: mantener `base.py` sin depender de módulos concretos; usar importaciones diferidas en relaciones.
- *Autenticación rota*: `User`/`Role` se mueven; validar startup `uvicorn` antes de merge.

## Fase B – Consola RBAC en Frontend

### 1. Endpoints involucrados
- `GET /api/users`
- `PUT /api/users/{id}` (cambia rol, estado, contraseña)
- `GET /api/roles`
- `GET /api/permissions`

### 2. Componentes nuevos
- `src/components/RbacAdminDialog.tsx`: tabla con usuarios, filtros rápidos y acciones (activar/desactivar, reset contraseña, asignar rol).
- `src/components/forms/RoleSelect.tsx`: reutilizable para otros panels.
- `src/hooks/use-rbac.ts`: encapsula llamadas a `apiClient` + cache local (`useState` + `useEffect`).

### 3. Flujo UI
1. Botón "Administrar Usuarios" visible solo si el token tiene permiso `users:manage` (se valida pidiendo `/api/users` y capturando 403).
2. Dialog muestra listado con columnas: Usuario, Email, Rol, Estado, Último acceso.
3. Acciones:
   - Cambiar rol: muestra `RoleSelect`, confirma con modal.
   - Reset contraseña: exige nueva contraseña + confirmación, envía `PUT`.
   - Toggle estado: quick action con toast.
4. Validaciones cliente: longitud de contraseña, coincidencia, bloqueo si usuario es system role (`is_system_role`).

### 4. Integración con modo Local/API
- Mostrar banner "Solo disponible en modo API" si `settings_use_api` es `false`.
- Si no hay token válido, pedir login (reutilizar flujo actual de autenticación).

### 5. QA
- Casos mínimos documentados en `TESTING_GUIDE.md`: crear usuario, cambiar rol, bloquear/desbloquear, intentar editar system role.
- Añadir snapshots manuales (capturas) para entrega final.

## Próximos pasos
1. Crear árbol `backend/app/models/` y migrar `User`, `Role`, `Permission` primero (menor riesgo).
2. Implementar `RbacAdminDialog` con tabla + RoleSelect; conectar a endpoints reales.
3. Documentar en `docs/PROD_INFRA_SECURITY.md` cómo gestionar usuarios via UI para que operaciones lo adopte.
