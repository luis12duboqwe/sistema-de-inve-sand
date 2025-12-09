# Copilot Instructions: Multi-Location Inventory System

## Project Overview

**Sistema de Inventario Multi-Ubicación v2.0** - A dual-mode inventory management system for mobile phones and accessories with multi-location warehousing, multiple sales channels (WhatsApp, Facebook, Instagram), and AI-powered insights.

**Tech Stack:**
- Frontend: React + TypeScript + Vite + TailwindCSS + Radix UI + GitHub Spark KV
- Backend: FastAPI + SQLAlchemy + SQLite
- Deployment: Dev containers (Debian 12)

## Critical Architecture Concepts

### Dual Storage Mode (Key Design Pattern)

The system supports **two backends** via `inventoryServiceFactory.ts`:

1. **Local Mode** (default): Data stored in **Spark KV** (browser IndexedDB abstraction) with localStorage fallback
2. **API Mode**: FastAPI backend with SQLite persistence

**Implementation Pattern:**
- `inventoryServiceFactory.ts` exports a factory that checks `settings_use_api` KV flag
- All data access goes through `IInventoryService` interface
- `localService` (from `inventoryService.ts`) for Spark KV operations
- `apiClient.ts` for REST API calls
- Never directly access KV or API - always use the factory

**Critical Rules:**
- When adding features, implement in BOTH `inventoryService.ts` and `apiClient.ts`
- Use `useKV` hook for settings/preferences, factory for business data
- Backend connection toggled in `SettingsDialog.tsx` - requires page reload

### V2.0 Multi-Location Architecture (Major Redesign)

**Old V1.0 (DEPRECATED):**
- `Profile` = business segment (Softmobile, TechStore) with own product catalog
- Stock tied to profiles

**New V2.0 (Current):**
- **`Location`** (backend: `models.Location`) = Physical place (Tienda 1, Bodega Central)
  - Each location has independent stock via `Stock.location_id`
  - Types: `tienda`, `bodega`, `oficina`
  
- **`SalesProfile`** (backend: `models.SalesProfile`) = Seller/bot/channel
  - Types: `bot_ia`, `vendedor_humano`, `sistema_automatico`
  - Can manage multiple channels: `['whatsapp', 'facebook', 'instagram']`
  - All profiles see **global product catalog** across all locations
  
- **`Product`** = Global catalog item (not tied to specific location)
  - `profile_id` field is LEGACY/nullable - kept for backward compatibility
  - `stock_items` relationship: List of `Stock` entries (one per location)
  - `stock_disponible` computed field: SUM of all location stocks

**Order Flow V2.0:**
```python
Order {
  sales_profile_id: 1,      # WHO sold (which bot/vendedor)
  source_location_id: 2,    # WHERE stock came from (which tienda/bodega)
  customer_name, customer_phone, canal, metodo_pago,
  items: [OrderItem{product_id, cantidad, precio_unitario}]
}
```

**Stock Transfers:**
- Endpoint: `POST /api/stock-transfers`
- Creates history entry + updates stock at both locations atomically
- Frontend: `StockByLocationDialog.tsx`, backend: `routers/stock_transfers.py`

### Database Schema Patterns

**Backend Models** (`backend/app/models.py`):
- Use SQLAlchemy ORM with explicit relationships
- All models have `created_at`, `updated_at` timestamps
- Composite indexes for common queries (e.g., `idx_location_tipo_activo`)
- Atomic transactions for multi-table operations (orders, stock transfers)

**Pydantic Schemas** (`backend/app/schemas.py`):
- Strict separation: `*Create` (input), `*Update` (partial), `*Response` (output)
- Enums: `CategoriaEnum`, `CondicionEnum`, `CanalEnum`, `MetodoPagoEnum`, `EstadoOrdenEnum`
- Validators use `@field_validator` decorator
- Pagination: `PaginatedResponse[T]` generic wrapper

**Frontend Types** (`src/lib/types.ts`):
- Mirror backend schemas but use TypeScript union types for enums
- `ProductWithStock` includes computed `stock_disponible` and `stock_items[]`
- `OrderWithItems` includes nested `items[]` with full product details

### Key File Locations

**Backend Routers:**
- `backend/app/routers/` - One file per resource
- Each router: `router = APIRouter(prefix="/api/[resource]", tags=["[resource]"])`
- Common pattern: Helper `_serialize_*()` functions for consistent responses

**Frontend Components:**
- `src/components/` - Dialog-based UI (Radix Dialog components)
- `src/lib/` - Services, utilities, types
- `src/hooks/` - Custom hooks (use-kv, use-forecasting, use-health-check, etc.)

**Critical Services:**
- `src/lib/inventoryServiceFactory.ts` - Main data access layer
- `src/lib/kvStorage.ts` - Spark KV abstraction with localStorage fallback
- `src/lib/apiClient.ts` - REST client with error handling

## Developer Workflows

### Starting the System

**Quick Start (Auto-test):**
```bash
./test-system.sh  # Validates env, runs backend tests, starts servers
```

**Manual Start:**
```bash
# Backend (Terminal 1)
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 init_db.py --with-data  # First time only
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (Terminal 2)
npm install
npm run dev  # Vite dev server on port 5173
```

**Windows:** Use `start-backend.bat` and `start-frontend.bat`

### Database Migrations

**No formal migration framework** - use Python scripts:
- `backend/init_db.py` - Fresh DB with optional test data
- `backend/migrate_to_locations_model.py` - V1→V2 migration
- Pattern: `backend/migrate_*.py` files for schema changes

**After model changes:**
1. Delete `backend/inventory.db`
2. Run `python3 init_db.py --with-data`
3. Or write migration script following existing patterns

### Testing

**Backend:**
```bash
cd backend
source venv/bin/activate
python3 test-backend.py  # Automated integration tests
```

**Frontend:**
- No unit tests configured
- Manual testing via UI
- Use `TESTING_GUIDE.md` checklist

**API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Examples: `api-examples-nuevo-sistema.json`

### Common Patterns

**Adding New Backend Endpoint:**
1. Add model to `backend/app/models.py` (if needed)
2. Add Pydantic schemas to `backend/app/schemas.py` (Create, Update, Response)
3. Create router in `backend/app/routers/[resource].py`
4. Register router in `backend/app/main.py`: `app.include_router([resource].router)`
5. Add TypeScript types to `src/lib/types.ts`
6. Add API client method to `src/lib/apiClient.ts`
7. Add local service method to `src/lib/inventoryService.ts`
8. Update factory interface in `src/lib/inventoryServiceFactory.ts`

**Adding New UI Feature:**
1. Create dialog component in `src/components/[Feature]Dialog.tsx`
2. Use Radix UI primitives (Dialog, Select, Input from `ui/`)
3. Access data via `inventoryServiceFactory.getService()`
4. Update state with `setProducts()`, `setOrders()`, etc. (from `useKV` hook in `App.tsx`)
5. Show toast notifications with `toast()` from `sonner`
6. Add keyboard shortcut via `useKeyboardShortcuts` if applicable

**Data Persistence Pattern:**
```typescript
// In App.tsx or components
const [products, setProducts] = useKV<ProductWithStock[]>('inventory-products', [])

// To update
const service = await inventoryServiceFactory.getService()
const newProduct = await service.createProduct({...})
setProducts(prev => [...prev, newProduct])  // Triggers KV save
```

## Project-Specific Conventions

### Naming Conventions
- Backend: `snake_case` (Python/SQL standard)
- Frontend: `camelCase` for variables, `PascalCase` for components/types
- Database tables: plural (e.g., `products`, `sales_profiles`)
- API routes: `/api/[resource]` (plural), e.g., `/api/products`

### Component Patterns
- Dialog components: `[Feature]Dialog.tsx` with `open`, `onOpenChange`, `onSuccess` props
- Card components: `[Resource]Card.tsx` for list items (ProductCard, OrderCard)
- List components: `[Resource]List.tsx` for V2 entities (LocationsList, SalesProfilesList)
- Use `motion.div` from Framer Motion for animations
- Error boundaries: `ErrorFallback.tsx` wraps entire app

### Code Comments
- **V1.0 LEGACY** comments mark deprecated code (kept for migration compatibility)
- **V2.0** comments mark new multi-location features
- **DEPRECATED** marks fields still in schema but not actively used

### State Management
- No Redux/Zustand - use React `useState` + `useKV` hook
- KV keys prefix: `inventory-*`, `settings-*`
- Settings persisted: `settings_use_api`, `settings_api_url`, `settings_sync_*`

### API Error Handling
```typescript
// Standard pattern in apiClient.ts
try {
  const response = await fetch(url, options)
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return await response.json()
} catch (error) {
  console.error('API Error:', error)
  throw error  // Let component handle with toast
}
```

### Advanced Features (Implemented)
- **AI Forecasting**: `use-forecasting.ts` - Linear regression for demand prediction
- **Optimization Insights**: `use-optimization-insights.ts` - Pricing/inventory recommendations
- **Real-time Sync**: `use-realtime-sync.ts` - Cross-tab synchronization via BroadcastChannel
- **Health Check**: `use-health-check.ts` - Backend connectivity monitoring
- **Stock History**: Track all stock movements (sales, transfers, adjustments)

## Common Pitfalls

1. **Forgetting dual-mode implementation**: Always update BOTH `inventoryService.ts` AND `apiClient.ts`
2. **Profile vs SalesProfile confusion**: In V2.0, `Profile` is legacy, use `SalesProfile` for sellers
3. **Stock calculation**: Always SUM `stock_items` for total, don't rely on single `stock` field
4. **Transactions**: Backend orders MUST use SQLAlchemy transactions to update stock atomically
5. **KV persistence**: Changes to state only persist if using `setX()` from `useKV` hook
6. **Page reload required**: After toggling API mode in settings, page MUST reload to switch backends

## Documentation References

- **Quick Start**: `INICIO_RAPIDO.md` - 3-step V2 setup
- **Architecture**: `NUEVO_SISTEMA_UBICACIONES.md` - V2.0 design details
- **API Examples**: `api-examples-nuevo-sistema.json` - cURL commands
- **Testing**: `TESTING_GUIDE.md` - Manual test checklist
- **Integration**: `INTEGRATION.md` - Dual-mode setup guide
- **Features**: `PRD.md` - Product requirements, feature list

## Special Notes

- **Dev Container**: Runs on Debian 12, includes Node.js, Python 3.11+, Git, SSH server
- **Ports**: Frontend 5173, Backend 8000 (configured in scripts)
- **Spark KV**: GitHub's IndexedDB wrapper - see `src/vite-end.d.ts` for type definitions
- **CORS**: Backend allows all origins in development (`settings.cors_origins` in `app/config.py`)
- **IMEIs**: Products can have multiple IMEIs (array field), old `imei` field kept for compatibility
- **Moneda**: Products support multiple currencies, stored as string field (e.g., "HNL", "USD")

---

**When in doubt**: Check existing implementations in both `inventoryService.ts` and `apiClient.ts`, follow the dual-mode pattern religiously, and ensure backend changes include corresponding Pydantic schemas.
