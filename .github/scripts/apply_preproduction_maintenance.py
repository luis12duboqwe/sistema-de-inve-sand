from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 match, found {count}")
    return text.replace(old, new, 1)


app_path = Path("src/App.tsx")
app = app_path.read_text(encoding="utf-8")

app = replace_once(
    app,
    "import { inventoryServiceFactory, inventoryServiceInstance } from '@/lib/inventoryServiceFactory'\n",
    "import { inventoryServiceFactory, inventoryServiceInstance } from '@/lib/inventoryServiceFactory'\n"
    "import { updateOrderStatusWithoutDailyClose } from '@/lib/orderStatusActions'\n"
    "import { buildMultiStoreViewModel, hasAppPermission } from '@/lib/appViewModel'\n",
    "App helper imports",
)

app = replace_once(
    app,
    "import { ValidationCodeDialog } from '@/components/ValidationCodeDialog'\n",
    "",
    "obsolete App validation dialog import",
)

app = replace_once(
    app,
    "  const [validationCodeRequest, setValidationCodeRequest] = useState<{\n"
    "    title: string\n"
    "    description: string\n"
    "    resolve: (code: string | null) => void\n"
    "  } | null>(null)\n",
    "",
    "obsolete App validation state",
)

app = replace_once(
    app,
    "  const hasPermission = (slug: string): boolean => {\n"
    "    if (!useAPI) return true\n"
    "    if (currentUser?.is_superuser) return true\n"
    "    return currentUser?.role?.permissions?.some(permission => permission.slug === slug) ?? false\n"
    "  }\n",
    "  const hasPermission = (slug: string): boolean => hasAppPermission(Boolean(useAPI), currentUser, slug)\n",
    "permission helper extraction",
)

old_view_model = """  const activeLocations = useMemo(() => (locations ?? []).filter(location => location.activo), [locations])
  const productsWithLocationTracking = useMemo(
    () => (products ?? []).filter(product => (product.stock_items?.length ?? 0) > 0),
    [products]
  )
  const totalTrackedUnits = useMemo(
    () => (products ?? []).reduce((total, product) => total + Number(product.stock_disponible || 0), 0),
    [products]
  )
  const outOfStockProducts = useMemo(
    () => (products ?? []).filter(product => Number(product.stock_disponible || 0) <= 0).length,
    [products]
  )
  const locatedOrders = useMemo(
    () => (orders ?? []).filter(order => order.source_location_id).length,
    [orders]
  )
  const locationSnapshots = useMemo(() => {
    return activeLocations
      .map(location => {
        const productsAtLocation = (products ?? []).filter(product =>
          product.stock_items?.some(stockItem => stockItem.location_id === location.id && Number(stockItem.cantidad_disponible || 0) > 0)
        )

        const unitsAtLocation = (products ?? []).reduce((total, product) => {
          const stockItem = product.stock_items?.find(item => item.location_id === location.id)
          return total + Number(stockItem?.cantidad_disponible || 0)
        }, 0)

        return {
          id: location.id,
          nombre: location.nombre,
          tipo: location.tipo,
          productsAtLocation: productsAtLocation.length,
          unitsAtLocation,
        }
      })
      .sort((a, b) => b.unitsAtLocation - a.unitsAtLocation)
      .slice(0, 4)
  }, [activeLocations, products])
"""
new_view_model = """  const {
    activeLocations,
    productsWithLocationTracking,
    totalTrackedUnits,
    outOfStockProducts,
    locatedOrders,
    locationSnapshots,
  } = useMemo(
    () => buildMultiStoreViewModel(locations ?? [], products ?? [], orders ?? []),
    [locations, products, orders]
  )
"""
app = replace_once(app, old_view_model, new_view_model, "multistore view-model extraction")

completion_start = app.find("  const getCompletionValidationCode = async (")
completion_end = app.find("  const handleBulkUpdateOrderStatus = async ", completion_start)
if completion_start == -1 or completion_end == -1:
    raise SystemExit("completion validation helper: expected block not found")
app = app[:completion_start] + app[completion_end:]

app = replace_once(
    app,
    "    try {\n"
    "      const validationCode = await getCompletionValidationCode(newStatus)\n"
    "      if (validationCode === null) return\n\n"
    "      if (useAPI) {\n"
    "        for (const orderId of selectedOrders) {\n"
    "          await service.updateOrderStatus(orderId, newStatus, validationCode)\n"
    "        }\n",
    "    try {\n"
    "      if (useAPI) {\n"
    "        for (const orderId of selectedOrders) {\n"
    "          await updateOrderStatusWithoutDailyClose(service, orderId, newStatus)\n"
    "        }\n",
    "bulk order completion separation",
)

app = replace_once(
    app,
    "                      onStatusChange={canEditOrders ? async (orderId, newStatus) => {\n"
    "                        const validationCode = await getCompletionValidationCode(newStatus)\n"
    "                        if (validationCode === null) return\n\n"
    "                        const updated = await service.updateOrderStatus(orderId, newStatus, validationCode)\n",
    "                      onStatusChange={canEditOrders ? async (orderId, newStatus) => {\n"
    "                        const updated = await updateOrderStatusWithoutDailyClose(service, orderId, newStatus)\n",
    "single order completion separation",
)

validation_dialog_start = app.find("      {validationCodeRequest && (\n")
validation_dialog_end_marker = "      <KeyboardShortcutsDialog\n"
validation_dialog_end = app.find(validation_dialog_end_marker, validation_dialog_start)
if validation_dialog_start == -1 or validation_dialog_end == -1:
    raise SystemExit("obsolete App validation dialog block: expected block not found")
app = app[:validation_dialog_start] + app[validation_dialog_end:]

if "getCompletionValidationCode" in app or "getDailyCloseConfig()" in app or "Validar venta" in app:
    raise SystemExit("sale completion still contains daily-close coupling after transformation")

app_path.write_text(app, encoding="utf-8")


ai_path = Path("backend/app/routers/ai_intelligence.py")
ai = ai_path.read_text(encoding="utf-8")
ai = replace_once(
    ai,
    "from app.services.forecasting_service import generate_sales_forecasts\n",
    "from app.services.forecasting_service import generate_sales_forecasts\n"
    "from app.services.ai_intelligence_helpers import (\n"
    "    build_fallback_recommendations as _build_fallback_recommendations,\n"
    "    ensure_aware_utc as _ensure_aware,\n"
    "    isoformat_optional as _isoformat,\n"
    "    parse_ai_business_response as _parse_ai_business_response,\n"
    "    safe_float as _safe_float,\n"
    ")\n",
    "AI helper imports",
)

ai_start = ai.find("\ndef _safe_float(value: Any) -> float:\n")
ai_end = ai.find("\n\nopenai_service = get_openai_service()", ai_start)
if ai_start == -1 or ai_end == -1:
    raise SystemExit("AI pure helper block: expected block not found")
ai = ai[:ai_start] + ai[ai_end:]
ai_path.write_text(ai, encoding="utf-8")


daily_path = Path("src/components/DailyCloseDialog.tsx")
daily = daily_path.read_text(encoding="utf-8")
daily = replace_once(
    daily,
    "            Cierre de Día — Validar Ventas\n",
    "            Cierre de Día — Validación de Ventas\n",
    "daily-close title",
)
daily = replace_once(
    daily,
    "            Revise las ventas completadas del día, ingrese el código de validación y confirme.\n"
    "            Solo las ventas validadas quedan registradas como definitivas en el historial.\n",
    "            Completar una venta registra la operación. Este cierre es un control separado: revise las ventas\n"
    "            completadas del día, ingrese el código de validación y confirme el cierre.\n",
    "daily-close description",
)
daily_path.write_text(daily, encoding="utf-8")

print("Pre-production maintenance transformation applied successfully")
