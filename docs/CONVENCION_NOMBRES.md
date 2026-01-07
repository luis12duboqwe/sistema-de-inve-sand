# 📘 Convención de Nombres v2.0

> Documento de referencia para QA y desarrollo continuo del sistema multi-ubicación. Resume cómo nombramos tablas, modelos, endpoints, componentes y estados internos.

## 1. Objetivos
- Evitar ambigüedades entre la herencia V1 (perfiles) y el modelo V2 (locations/sales_profiles).
- Asegurar que backend y base de datos sigan `snake_case`, mientras que la UI expone `camelCase` en estados/reglas internas.
- Documentar mapeos clave para que QA pueda detectar regresiones o payloads inconsistentes.

## 2. Reglas generales
- **Lenguaje**: identificadores en español cuando representan conceptos del negocio (ej. `retoma`, `bodega`), inglés solo para abreviaturas técnicas (`DTO`, `API`, `JWT`).
- **Prefijos**: evita abreviaturas crípticas. Usa `sales_profile`, `stock_transfer`, `ai_profile` completo en tablas, rutas y archivos.
- **Contexto**: cada archivo debe nombrarse por el dominio que encapsula (`TradeInPoliciesDialog`, `stock_transaction_helper`).

## 3. Backend (Python / FastAPI)
- **Módulos**: archivos en `app/` siempre `snake_case`. Ej.: `stock_transaction_helper.py`, `auth_router.py`.
- **Clases**: `PascalCase` (`StockManager`, `TradeInPolicy`).
- **Funciones y métodos**: `snake_case` (`prepare_sale_items`, `process_trade_ins`).
- **Constantes**: `UPPER_SNAKE_CASE` (`DEFAULT_BATCH_SIZE`).
- **Dependencias FastAPI**: si devuelven un recurso específico, prefijo `get_` (`get_current_user`).
- **Exceptions personalizadas**: sufijo `Error` (`StockValidationError`).

### Base de datos (SQLAlchemy / PostgreSQL)
- **Tablas**: plural `snake_case`. Ej.: `products`, `sales_profiles`, `stock_transfers`.
- **Columnas**: `snake_case`. Usa sufijo `_id` para llaves foráneas (`location_id`).
- **Índices**: prefijo `idx_<tabla>_<columna>`.
- **Campos legacy**: marca con comentario `# LEGACY` en el modelo hasta eliminarlo (`profile_id` en `Product`).
- **Relaciones**: propiedades en modelos usan nombres descriptivos (`stock_items`, `trade_ins`).

### Pydantic Schemas
- Inputs `*Create` / `*Update` mantienen el mismo `snake_case` que la BD.
- Respuestas `*Response` exponen `snake_case` por compatibilidad API.
- Enum/choices declarados en inglés pero valores devueltos en español (ej. `LocationTypeEnum.tienda -> "tienda"`).

## 4. API REST
- Prefijo `/api/<recurso>` plural. Ej.: `/api/orders`, `/api/stock-transfers`.
- IDs y filtros en query params usan `snake_case` (`sales_profile_id`, `location_id`).
- Versionado implícito vía payload (no usar `/v1`).
- Errores: objeto `{ "detail": "mensaje" }` en español.

## 5. Frontend (TypeScript / React)
- **Componentes**: `PascalCase` (`PendingTradeInsDialog`).
- **Hooks**: prefijo `use` + `PascalCase` (`useRbac`, `useKV`).
- **Utilidades**: `camelCase` (`formatPrice`, `inventoryServiceFactory`).
- **Interfaces/Types**: `PascalCase`. Campos reflejan el backend (se conserva `snake_case` para payloads) pero los estados derivados usan `camelCase`.
  - Ej.: interfaz `ProductWithStock` incluye `stock_disponible`; al derivar estado local usar `stockDisponible`.
- **Zustand/Context** (si se agregan): claves `camelCase` (`userRole`, `selectedLocation`).
- **Archivos**:
  - Componentes React: `src/components/<Feature>.tsx`.
  - Hooks: `src/hooks/use-<feature>.ts`.
  - Validaciones compartidas: `src/lib/validation/<dominio>.ts` manteniendo nombres descriptivos (`tradeInActivationSchema`).

## 6. Mapeo rápido Backend ↔ Frontend
| Dominio | Tabla / Modelo | Campo API (`snake_case`) | Propiedad UI (`camelCase`) |
| --- | --- | --- | --- |
| Productos | `products` / `Product` | `stock_disponible` | `stockDisponible` (solo si se transforma) |
| Ubicaciones | `locations` / `Location` | `tipo`, `activo` | `tipo`, `activo` (igual que API) |
| Perfiles de venta | `sales_profiles` / `SalesProfile` | `canales`, `configuracion` | `channels` (alias opcional para UI), `config` |
| Transferencias | `stock_transfers` / `StockTransfer` | `source_location_id`, `dest_location_id` | `sourceLocationId`, `destLocationId` |
| RBAC | `users`, `roles`, `permissions` | `is_system_role`, `permissions` | `isSystemRole`, `permissions` |

> Nota: solo se crean alias `camelCase` cuando el dato se reutiliza extensivamente en lógica UI o librerías externas. Caso contrario, se conserva `snake_case` para evitar mapeos innecesarios.

## 7. Archivos y carpetas
- `backend/app/models/`: submódulos por dominio (`product.py`, `order.py`, `location.py`, `user.py`).
- `backend/app/schemas/`: espejo de los modelos.
- `backend/app/services/`: sufijo `_service` o `_helper` según responsabilidad.
- `docs/`: títulos en mayúscula con guiones bajos (`RBAC_REFACTOR_PLAN.md`).
- `deploy/`: archivos de infraestructura con prefijo descriptivo (`docker-compose.prod.yml`, `nginx.conf`).
- `src/components`: prefijo del recurso (`OrdersList.tsx`, `RbacAdminDialog.tsx`).

## 8. Ejemplo completo – Alta de orden con retoma
1. **Backend**
   - Modelo `Order` en `order.py` (tabla `orders`).
   - Servicio `stock_transaction_helper.prepare_sale_items`.
2. **API**
   - Endpoint `POST /api/orders` recibe `items`, `trade_ins`, `source_location_id` en `snake_case`.
3. **Frontend**
   - Formulario `NewOrderDialog` mantiene payload `snake_case`.
   - Estado local `newOrderTotals` usa `camelCase` (`totalAfterTradeIns`).
4. **Documentación**
   - Ejemplo cURL va en `api-examples-nuevo-sistema.json` usando los mismos nombres.

Con esta convención alineamos BD, backend y frontend, facilitamos el refactor modular y sentamos las bases para la nueva consola RBAC.
