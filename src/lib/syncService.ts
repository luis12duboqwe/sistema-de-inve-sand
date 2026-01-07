import { apiClient } from './apiClient'
import { getKV } from './kvStorage'
import { syncJournal } from './syncJournal'
import type {
  SyncEvent,
  SyncEntityType,
  Profile,
  SalesProfile,
  Location,
  Product,
  ProductWithStock,
  Stock,
  Order,
  OrderWithItems,
  OrderItem,
  CreateOrderRequest,
  StockTransfer,
  CreateStockTransferRequest,
  Return,
  CreateReturnRequest,
  ReturnItem,
  TradeIn,
  ProductIMEI,
  IMEIHistory,
  StockHistory,
  Customer,
  TrainingQueueItem,
  Bank,
  FinancingOption,
  TradeInPolicy,
  FAQEntry,
  User,
  Role,
  Permission
} from './types'

type SyncIdMap = Record<string, number | string>

type SyncResult = {
  processed: number
  synced: number
  failed: number
  total: number
  snapshot?: SnapshotCounts
  pendingEvents?: number
}

type SyncOptions = {
  batchSize?: number
  onProgress?: (event: SyncProgressEvent) => void
  signal?: AbortSignal
}

export type SyncProgressEvent = {
  status: 'processing' | 'success' | 'error'
  processed: number
  total: number
  event: SyncEvent
  error?: string
}

type SnapshotCounts = {
  profiles: number
  salesProfiles: number
  locations: number
  products: number
  stockEntries: number
  orders: number
  orderItems: number
  stockTransfers: number
  returns: number
  customers: number
  productImeis: number
  imeiHistoryEntries: number
  stockHistoryEntries: number
}

type HandlerResult = {
  metadata?: Record<string, any>
  newIds?: Array<{
    entity: SyncEntityType
    localId: number | string
    remoteId: number | string
  }>
}

interface SyncContext {
  kv: ReturnType<typeof getKV>
  idMap: SyncIdMap
  profiles: Profile[]
  salesProfiles: SalesProfile[]
  locations: Location[]
}

const SYNC_ID_MAP_KEY = 'sync-id-map'
const DEFAULT_BATCH_SIZE = 25
const PENDING_SYNC_FLAG_KEY = 'settings_pending_sync'

export const syncService = {
  async syncLocalToRemote(options: SyncOptions = {}): Promise<SyncResult> {
    const kv = getKV()
    const pendingEvents = await syncJournal.getPendingEvents()
    await kv.set(PENDING_SYNC_FLAG_KEY, pendingEvents.length > 0)

    await runPreflightChecks(kv)

    if (!pendingEvents.length) {
      return { processed: 0, synced: 0, failed: 0, total: 0, pendingEvents: 0 }
    }

    const context = await buildSyncContext(kv)
    const sortedEvents = [...pendingEvents].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )
    const batches = chunkEvents(sortedEvents, options.batchSize ?? DEFAULT_BATCH_SIZE)

    const summary: SyncResult = {
      processed: 0,
      synced: 0,
      failed: 0,
      total: pendingEvents.length
    }

    for (const batch of batches) {
      for (const event of batch) {
        throwIfAborted(options.signal)
        summary.processed += 1
        options.onProgress?.({
          status: 'processing',
          processed: summary.processed,
          total: summary.total,
          event
        })

        try {
          const handlerResult = await processEvent(event, context)
          const metadata = await persistHandlerResult(handlerResult, context)
          await syncJournal.markSynced(event.id, metadata ? { metadata } : undefined)
          summary.synced += 1
          options.onProgress?.({
            status: 'success',
            processed: summary.processed,
            total: summary.total,
            event
          })
        } catch (error) {
          const message = formatError(error)
          await syncJournal.markError(event.id, message)
          summary.failed += 1
          options.onProgress?.({
            status: 'error',
            processed: summary.processed,
            total: summary.total,
            event,
            error: message
          })
        }
      }
    }

    if (summary.synced > 0 && summary.failed === 0) {
      summary.snapshot = await refreshLocalSnapshot(kv)
      await kv.delete(SYNC_ID_MAP_KEY)
    }

    await syncJournal.clearSyncedEvents()

    const remainingEvents = await syncJournal.getPendingEvents()
    summary.pendingEvents = remainingEvents.length
    await kv.set(PENDING_SYNC_FLAG_KEY, remainingEvents.length > 0)

    return summary
  }
}

async function runPreflightChecks(kv: ReturnType<typeof getKV>): Promise<void> {
  const useApi = await kv.get<boolean>('settings_use_api')
  if (!useApi) {
    throw new Error('Activa el modo API para iniciar la sincronización con el backend.')
  }

  if (!apiClient.getToken()) {
    throw new Error('Inicia sesión para autenticarte contra el backend antes de sincronizar.')
  }

  await apiClient.checkHealth()
}

async function buildSyncContext(kv: ReturnType<typeof getKV>): Promise<SyncContext> {
  const [idMapRaw, profiles, salesProfiles, locations] = await Promise.all([
    kv.get<SyncIdMap>(SYNC_ID_MAP_KEY),
    kv.get<Profile[]>('inventory-profiles'),
    kv.get<SalesProfile[]>('inventory-sales-profiles'),
    kv.get<Location[]>('inventory-locations')
  ])

  return {
    kv,
    idMap: idMapRaw ?? {},
    profiles: profiles ?? [],
    salesProfiles: salesProfiles ?? [],
    locations: locations ?? []
  }
}

function chunkEvents<T>(items: T[], requestedSize: number): T[][] {
  const size = Math.max(1, requestedSize)
  const result: T[][] = []
  for (let index = 0; index < items.length; index += size) {
    result.push(items.slice(index, index + size))
  }
  return result
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) {
    const reason = typeof signal.reason === 'string' ? signal.reason : 'La sincronización fue cancelada.'
    throw new Error(reason)
  }
}

async function processEvent(event: SyncEvent, context: SyncContext): Promise<HandlerResult | void> {
  switch (event.entity) {
    case 'location':
      return handleLocationEvent(event, context)
    case 'sales_profile':
      return handleSalesProfileEvent(event, context)
    case 'profile':
      return handleProfileEvent(event, context)
    case 'product':
      return handleProductEvent(event, context)
    case 'stock':
      return handleStockEvent(event, context)
    case 'order':
      return handleOrderEvent(event, context)
    case 'stock_transfer':
      return handleStockTransferEvent(event, context)
    case 'return':
      return handleReturnEvent(event, context)
    case 'imei':
      return handleImeiEvent(event)
    default:
      throw new Error(`No hay un manejador implementado para ${event.entity}:${event.action}`)
  }
}

async function persistHandlerResult(result: HandlerResult | void, context: SyncContext): Promise<Record<string, any> | undefined> {
  if (!result) {
    return undefined
  }

  if (result.newIds?.length) {
    for (const mapping of result.newIds) {
      if (mapping.localId === undefined || mapping.localId === null) {
        continue
      }
      await recordRemoteId(context, mapping.entity, mapping.localId, mapping.remoteId)
    }
  }

  return result.metadata
}

async function handleLocationEvent(event: SyncEvent, context: SyncContext): Promise<HandlerResult> {
  const payload = event.payload ?? {}

  switch (event.action) {
    case 'create': {
      const location = payload.location as Location | undefined
      if (!location) {
        throw new Error('El evento de ubicación no contiene datos a crear.')
      }

      const { id, created_at: _created, updated_at: _updated, ...rest } = location
      const created = await apiClient.createLocation({
        nombre: rest.nombre,
        tipo: rest.tipo,
        direccion: rest.direccion,
        telefono: rest.telefono,
        activo: rest.activo
      })

      return {
        metadata: { remote_id: created.id },
        newIds: id !== undefined ? [{ entity: 'location', localId: id, remoteId: created.id }] : undefined
      }
    }
    case 'update': {
      const updates = payload.updates ?? payload.after
      if (!updates) {
        return { metadata: { note: 'Ubicación sin cambios pendientes.' } }
      }

      const remoteId = resolveNumericRemoteId(context, 'location', event.entityId ?? payload.after?.id)
      const { id: _ignored, created_at: _created, updated_at: _updated, ...partial } = updates
      await apiClient.updateLocation(remoteId, partial)
      return { metadata: { remote_id: remoteId } }
    }
    case 'delete': {
      const remoteId = resolveNumericRemoteId(context, 'location', event.entityId ?? payload.location?.id)
      await apiClient.deleteLocation(remoteId)
      return { metadata: { remote_id: remoteId } }
    }
    default:
      throw new Error(`Acción ${event.action} no soportada para locations.`)
  }
}

async function handleSalesProfileEvent(event: SyncEvent, context: SyncContext): Promise<HandlerResult> {
  const payload = event.payload ?? {}

  switch (event.action) {
    case 'create': {
      const profile = payload.profile as SalesProfile | undefined
      if (!profile) {
        throw new Error('El evento de sales_profile no contiene datos de perfil.')
      }

      const { id, created_at: _created, updated_at: _updated, ...rest } = profile
      const created = await apiClient.createSalesProfile({
        name: rest.name,
        slug: rest.slug,
        tipo: rest.tipo,
        canales: rest.canales,
        configuracion: rest.configuracion,
        active: rest.active
      })

      return {
        metadata: { remote_id: created.id },
        newIds: id !== undefined ? [{ entity: 'sales_profile', localId: id, remoteId: created.id }] : undefined
      }
    }
    case 'update': {
      const updates = payload.updates ?? payload.after
      if (!updates) {
        return { metadata: { note: 'Sales profile sin cambios pendientes.' } }
      }
      const remoteId = resolveNumericRemoteId(context, 'sales_profile', event.entityId ?? payload.after?.id)
      const { id: _ignored, created_at: _created, updated_at: _updated, ...partial } = updates
      await apiClient.updateSalesProfile(remoteId, partial)
      return { metadata: { remote_id: remoteId } }
    }
    case 'delete': {
      const remoteId = resolveNumericRemoteId(context, 'sales_profile', event.entityId ?? payload.profile?.id)
      await apiClient.deleteSalesProfile(remoteId)
      return { metadata: { remote_id: remoteId } }
    }
    default:
      throw new Error(`Acción ${event.action} no soportada para sales_profile.`)
  }
}

async function handleProfileEvent(event: SyncEvent, context: SyncContext): Promise<HandlerResult> {
  const payload = event.payload ?? {}

  switch (event.action) {
    case 'create': {
      const profile = payload.profile as Profile | undefined
      if (!profile) {
        throw new Error('El evento de profile no contiene datos a crear.')
      }

      const created = await apiClient.createProfile(profile.name, profile.slug)
      return {
        metadata: { remote_id: created.id },
        newIds: profile.id !== undefined ? [{ entity: 'profile', localId: profile.id, remoteId: created.id }] : undefined
      }
    }
    case 'update': {
      const updates = payload.updates ?? payload.after
      if (!updates) {
        return { metadata: { note: 'Profile sin cambios pendientes.' } }
      }

      const remoteId = resolveNumericRemoteId(context, 'profile', event.entityId ?? payload.after?.id)
      const body: { name?: string; active?: boolean } = {}
      if (typeof updates.name === 'string') {
        body.name = updates.name
      }
      if (typeof updates.active === 'boolean') {
        body.active = updates.active
      }

      if (!Object.keys(body).length) {
        return { metadata: { remote_id: remoteId, note: 'Sin cambios relevantes.' } }
      }

      await apiClient.updateProfile(remoteId, body)
      return { metadata: { remote_id: remoteId } }
    }
    default:
      throw new Error(`Acción ${event.action} no soportada para profiles.`)
  }
}

async function handleProductEvent(event: SyncEvent, context: SyncContext): Promise<HandlerResult> {
  const payload = event.payload ?? {}

  switch (event.action) {
    case 'create': {
      if (payload.products) {
        throw new Error('Aún no se soporta la sincronización de cargas masivas de productos.')
      }

      const product = payload.product as Product | undefined
      if (!product) {
        throw new Error('El evento de producto no contiene datos a crear.')
      }

      const initialStock = typeof payload.initialStock === 'number' ? payload.initialStock : 0
      const locationId = payload.location_id ?? null
      const { id, activo: _activo, created_at: _created, updated_at: _updated, ...rest } = product

      const created = await apiClient.createProduct(
        rest as Omit<Product, 'id' | 'activo'>,
        initialStock,
        locationId ?? undefined
      )

      return {
        metadata: { remote_id: created.id },
        newIds: id !== undefined ? [{ entity: 'product', localId: id, remoteId: created.id }] : undefined
      }
    }
    case 'update': {
      const updates = payload.updates
      if (!updates || Object.keys(updates).length === 0) {
        return { metadata: { note: 'Producto sin cambios pendientes.' } }
      }

      const remoteId = resolveNumericRemoteId(context, 'product', event.entityId)
      await apiClient.updateProduct(remoteId, updates)
      return { metadata: { remote_id: remoteId } }
    }
    case 'delete': {
      const remoteId = resolveNumericRemoteId(context, 'product', event.entityId ?? payload.product_id)
      await apiClient.deleteProduct(remoteId)
      return { metadata: { remote_id: remoteId } }
    }
    default:
      throw new Error(`Acción ${event.action} no soportada para productos.`)
  }
}

async function handleStockEvent(event: SyncEvent, context: SyncContext): Promise<HandlerResult> {
  const payload = event.payload ?? {}
  const productId = resolveNumericRemoteId(context, 'product', payload.product_id)
  const locationId = resolveNumericRemoteId(context, 'location', payload.location_id)

  if (typeof payload.cantidad !== 'number') {
    throw new Error('El evento de stock no incluye la cantidad a aplicar.')
  }

  await apiClient.updateStock(productId, payload.cantidad, locationId)
  return {
    metadata: {
      remote_id: `${productId}:${locationId}`,
      product_id: productId,
      location_id: locationId
    }
  }
}

async function handleOrderEvent(event: SyncEvent, context: SyncContext): Promise<HandlerResult> {
  const payload = event.payload ?? {}

  switch (event.action) {
    case 'create': {
      const order = payload.order as Order | undefined
      const items = (payload.items as OrderItem[] | undefined) ?? order?.items
      if (!order || !items) {
        throw new Error('El evento de orden no tiene información suficiente para recrearse en el backend.')
      }

      const request = buildOrderCreateRequest(order, items, payload, context)
      const created = await apiClient.createOrder(request)
      return {
        metadata: { remote_id: created.id },
        newIds: order.id !== undefined ? [{ entity: 'order', localId: order.id, remoteId: created.id }] : undefined
      }
    }
    case 'update': {
      const remoteOrderId = resolveNumericRemoteId(context, 'order', event.entityId ?? payload.order_after?.id)
      const updates = normalizeOrderUpdates(payload.updates, context)
      await apiClient.updateOrder(remoteOrderId, updates)
      return { metadata: { remote_id: remoteOrderId } }
    }
    case 'cancel': {
      const remoteOrderId = resolveNumericRemoteId(context, 'order', event.entityId ?? payload.order_before?.id)
      await apiClient.cancelOrder(remoteOrderId, payload.reason)
      return { metadata: { remote_id: remoteOrderId } }
    }
    case 'delete': {
      const remoteOrderId = resolveNumericRemoteId(context, 'order', event.entityId ?? payload.order?.id)
      await apiClient.deleteOrder(remoteOrderId)
      return { metadata: { remote_id: remoteOrderId } }
    }
    default:
      throw new Error(`Acción ${event.action} no soportada para órdenes.`)
  }
}

async function handleStockTransferEvent(event: SyncEvent, context: SyncContext): Promise<HandlerResult> {
  const payload = event.payload ?? {}
  const transfer = payload.transfer as StockTransfer | undefined

  switch (event.action) {
    case 'create': {
      if (!transfer) {
        throw new Error('El evento de transferencia no incluye datos del registro a crear.')
      }

      const request = buildStockTransferCreateRequest(transfer, payload, context)
      const created = await apiClient.createStockTransfer(request)
      return {
        metadata: { remote_id: created.id },
        newIds:
          transfer.id !== undefined
            ? [{ entity: 'stock_transfer', localId: transfer.id, remoteId: created.id }]
            : undefined
      }
    }
    case 'confirm': {
      const remoteId = resolveNumericRemoteId(context, 'stock_transfer', event.entityId ?? transfer?.id)
      const confirmedBy = payload.confirmed_by ?? transfer?.confirmed_by ?? 'sistema'
      const scannedImeis = getStringArray(payload.scanned_imeis)
      await apiClient.confirmStockTransfer(remoteId, confirmedBy, scannedImeis?.length ? scannedImeis : undefined)
      return { metadata: { remote_id: remoteId } }
    }
    case 'reject': {
      const remoteId = resolveNumericRemoteId(context, 'stock_transfer', event.entityId ?? transfer?.id)
      const rejectedBy = payload.rejected_by ?? transfer?.confirmed_by ?? 'sistema'
      const reason = payload.rejection_reason ?? transfer?.rejection_reason ?? 'Transferencia rechazada desde modo offline.'
      await apiClient.rejectStockTransfer(remoteId, rejectedBy, reason)
      return { metadata: { remote_id: remoteId } }
    }
    case 'cancel': {
      const remoteId = resolveNumericRemoteId(context, 'stock_transfer', event.entityId ?? transfer?.id)
      await apiClient.cancelStockTransfer(remoteId)
      return { metadata: { remote_id: remoteId } }
    }
    default:
      throw new Error(`Acción ${event.action} no soportada para transferencias de stock.`)
  }
}

async function handleReturnEvent(event: SyncEvent, context: SyncContext): Promise<HandlerResult> {
  if (event.action !== 'create') {
    throw new Error(`Acción ${event.action} no soportada para devoluciones.`)
  }

  const payload = event.payload ?? {}
  const returnData = payload.return as Return | undefined
  if (!returnData) {
    throw new Error('El evento de devolución no incluye datos para sincronizar.')
  }

  const remoteOrderId = resolveNumericRemoteId(context, 'order', returnData.order_id ?? payload.order_id)
  const items = buildReturnItems(returnData.items ?? payload.items, context)
  if (!items.length) {
    throw new Error('La devolución no contiene artículos válidos para sincronizar.')
  }

  const request: CreateReturnRequest = {
    order_id: remoteOrderId,
    reason: returnData.reason ?? payload.reason,
    created_by: returnData.created_by ?? payload.created_by,
    items
  }

  const created = await apiClient.createReturn(request)
  return {
    metadata: { remote_id: created.id, order_id: remoteOrderId },
    newIds:
      returnData.id !== undefined
        ? [{ entity: 'return', localId: returnData.id, remoteId: created.id }]
        : undefined
  }
}

async function handleImeiEvent(event: SyncEvent): Promise<HandlerResult> {
  return {
    metadata: {
      note: 'Evento IMEI marcado como sincronizado localmente. La API maneja IMEIs a través de órdenes y transferencias.',
      action: event.action
    }
  }
}

function buildStockTransferCreateRequest(
  transfer: StockTransfer,
  payload: Record<string, any>,
  context: SyncContext
): CreateStockTransferRequest {
  const productId = resolveNumericRemoteId(context, 'product', transfer.product_id ?? payload.product_id)
  const fromLocationId = resolveNumericRemoteId(
    context,
    'location',
    transfer.from_location_id ?? payload.from_location_id
  )
  const toLocationId = resolveNumericRemoteId(context, 'location', transfer.to_location_id ?? payload.to_location_id)
  const quantity = typeof transfer.cantidad === 'number' ? transfer.cantidad : payload.cantidad
  if (typeof quantity !== 'number') {
    throw new Error('La transferencia no especifica la cantidad a sincronizar.')
  }

  const request: CreateStockTransferRequest = {
    product_id: productId,
    from_location_id: fromLocationId,
    to_location_id: toLocationId,
    cantidad: quantity,
    notas: transfer.notas ?? payload.notas,
    created_by: transfer.created_by ?? payload.created_by
  }

  const imeis = extractTransferImeis(payload, transfer)
  if (imeis?.length) {
    request.imeis = imeis
  }

  return request
}

function buildReturnItems(items: ReturnItem[] | undefined, context: SyncContext): ReturnItem[] {
  if (!items) {
    return []
  }

  return items.map(item => ({
    ...item,
    product_id: resolveNumericRemoteId(context, 'product', item.product_id)
  }))
}

function extractTransferImeis(payload: Record<string, any>, transfer?: StockTransfer): string[] | undefined {
  if (Array.isArray(transfer?.imeis) && transfer!.imeis!.length) {
    return transfer!.imeis!.slice()
  }

  const reserved = payload.imeis_reserved
  if (Array.isArray(reserved)) {
    const imeis = reserved
      .map(entry => (typeof entry?.imei === 'string' ? entry.imei.trim() : undefined))
      .filter((imei): imei is string => Boolean(imei))
    if (imeis.length) {
      return imeis
    }
  }

  return undefined
}

function getStringArray(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) {
    return undefined
  }
  const result = value
    .map(entry => (typeof entry === 'string' ? entry.trim() : undefined))
    .filter((entry): entry is string => Boolean(entry))
  return result.length ? result : undefined
}

function buildOrderCreateRequest(
  order: Order,
  items: OrderItem[],
  payload: Record<string, any>,
  context: SyncContext
): CreateOrderRequest {
  const sourceLocationLocalId = order.source_location_id ?? payload.source_location_id
  if (sourceLocationLocalId === undefined || sourceLocationLocalId === null) {
    throw new Error('La orden no especifica la ubicación origen (source_location_id).')
  }
  const sourceLocationId = resolveNumericRemoteId(context, 'location', sourceLocationLocalId)

  const mappedItems = items.map(item => ({
    product_id: resolveNumericRemoteId(context, 'product', item.product_id),
    cantidad: item.cantidad,
    imeis: item.imeis,
    precio_unitario: item.precio_unitario,
    es_regalo_promocion: item.es_regalo_promocion
  }))

  const salesProfileSlug = resolveSalesProfileSlug(context, order.sales_profile_id, (order as any).sales_profile_slug)
  const profileSlug = resolveProfileSlug(context, order.profile_id, (order as any).profile_slug)

  if (!salesProfileSlug && !profileSlug) {
    throw new Error('No se pudo determinar el perfil de ventas asociado a la orden.')
  }

  const tradeIns = payload.trade_ins ?? (order as any).trade_ins

  const request: CreateOrderRequest = {
    sales_profile_slug: salesProfileSlug,
    profile_slug: profileSlug,
    source_location_id: sourceLocationId,
    canal: order.canal,
    customer_name: order.customer_name,
    customer_phone: order.customer_phone,
    metodo_pago: order.metodo_pago,
    items: mappedItems,
    trade_ins: tradeIns,
    notas: order.notas ?? payload.notes ?? payload.notas,
    financing_data: payload.financing_data ?? order.financing_data
  }

  return request
}

function normalizeOrderUpdates(updates: any, context: SyncContext): Record<string, any> {
  if (!updates) {
    throw new Error('El evento de actualización de orden no incluye los cambios a aplicar.')
  }

  const normalized: Record<string, any> = { ...updates }

  if (Array.isArray(normalized.items)) {
    normalized.items = normalized.items.map((item: OrderItem) => ({
      ...item,
      product_id: resolveNumericRemoteId(context, 'product', item.product_id)
    }))
  }

  return normalized
}

function resolveSalesProfileSlug(
  context: SyncContext,
  salesProfileId?: number | null,
  fallbackSlug?: string
): string | undefined {
  if (fallbackSlug) {
    return fallbackSlug
  }
  if (salesProfileId === null || salesProfileId === undefined) {
    return undefined
  }
  return context.salesProfiles.find(sp => sp.id === salesProfileId)?.slug
}

function resolveProfileSlug(
  context: SyncContext,
  profileId?: number | null,
  fallbackSlug?: string
): string | undefined {
  if (fallbackSlug) {
    return fallbackSlug
  }
  if (profileId === null || profileId === undefined) {
    return undefined
  }
  return context.profiles.find(profile => profile.id === profileId)?.slug
}

async function recordRemoteId(
  context: SyncContext,
  entity: SyncEntityType,
  localId: number | string,
  remoteId: number | string
): Promise<void> {
  const key = buildIdMapKey(entity, localId)
  context.idMap[key] = remoteId
  await context.kv.set(SYNC_ID_MAP_KEY, context.idMap)
}

function resolveRemoteId(
  context: SyncContext,
  entity: SyncEntityType,
  localId?: number | string | null
): number | string | undefined {
  if (localId === null || localId === undefined) {
    return undefined
  }
  const key = buildIdMapKey(entity, localId)
  return context.idMap[key] ?? localId
}

function resolveNumericRemoteId(
  context: SyncContext,
  entity: SyncEntityType,
  localId?: number | string | null
): number {
  const resolved = resolveRemoteId(context, entity, localId)
  if (resolved === undefined) {
    throw new Error(`No se pudo resolver el identificador remoto para ${entity} (${String(localId)}).`)
  }

  const numeric = typeof resolved === 'string' ? Number(resolved) : resolved
  if (typeof numeric !== 'number' || Number.isNaN(numeric)) {
    throw new Error(`El identificador remoto para ${entity} (${String(resolved)}) no es numérico.`)
  }

  return numeric
}

function buildIdMapKey(entity: SyncEntityType, localId: number | string): string {
  return `${entity}:${localId}`
}

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  if (typeof error === 'string') {
    return error
  }
  try {
    return JSON.stringify(error)
  } catch {
    return 'Error desconocido en sincronización.'
  }
}

async function refreshLocalSnapshot(kv: ReturnType<typeof getKV>): Promise<SnapshotCounts> {
  const [profiles, salesProfiles, locations, products, orders] = await Promise.all([
    apiClient.listProfiles(),
    apiClient.listSalesProfiles(),
    apiClient.listLocations(false),
    apiClient.fetchProducts(undefined, undefined, true),
    apiClient.fetchOrders()
  ])

  type FaqListResponse = { items?: FAQEntry[]; total?: number; pages?: number }

  const [
    stockTransfers,
    returns,
    customers,
    trainingQueue,
    banks,
    faqResponse,
    tradeInPolicies,
    users,
    roles,
    permissions,
    productImeis,
    imeiHistory,
    stockHistoryEntries
  ] = await Promise.all([
    safeFetch(() => apiClient.listStockTransfers(), [] as StockTransfer[], 'stock transfers'),
    safeFetch(() => apiClient.getReturns(), [] as Return[], 'returns'),
    safeFetch(() => apiClient.listCustomers(), [] as Customer[], 'customers'),
    safeFetch(() => apiClient.listTrainingQueue('pending'), [] as TrainingQueueItem[], 'training queue'),
    safeFetch(() => apiClient.getBanks(false), [] as Bank[], 'banks'),
    safeFetch<FaqListResponse>(() => apiClient.listFAQs({ per_page: 200, page: 1 }), { items: [] }, 'faqs'),
    safeFetch(() => apiClient.getTradeInPolicies(), [] as TradeInPolicy[], 'trade-in policies'),
    safeFetch(() => apiClient.listUsers(), [] as User[], 'users'),
    safeFetch(() => apiClient.listRoles(), [] as Role[], 'roles'),
    safeFetch(() => apiClient.listPermissions(), [] as Permission[], 'permissions'),
    safeFetch(() => apiClient.fetchProductIMEIs(), [] as ProductIMEI[], 'product imeis'),
    safeFetch(() => apiClient.fetchIMEIHistoryEntries({ days: 120 }), [] as IMEIHistory[], 'imei history'),
    safeFetch(() => collectStockHistorySnapshot(locations), [] as StockHistory[], 'stock history')
  ])

  const orderRecords: Order[] = orders.map(({ items, ...order }) => ({ ...order } as Order))
  const stockRecords = buildStockRecords(products)
  const orderItems = flattenOrderItems(orders)
  const tradeIns = flattenTradeIns(orders)
  const financingOptions = extractFinancingOptions(banks)
  const faqs = faqResponse.items ?? []

  await Promise.all([
    kv.set('inventory-profiles', profiles),
    kv.set('inventory-sales-profiles', salesProfiles),
    kv.set('inventory-locations', locations),
    kv.set('inventory-products', products),
    kv.set('inventory-stock', stockRecords),
    kv.set('inventory-orders', orderRecords),
    kv.set('inventory-order-items', orderItems),
    kv.set('inventory-stock-transfers', stockTransfers),
    kv.set('inventory-returns', returns),
    kv.set('inventory-trade-ins', tradeIns),
    kv.set('inventory-customers', customers),
    kv.set('inventory-training-queue', trainingQueue),
    kv.set('inventory-banks', banks),
    kv.set('inventory-financing-options', financingOptions),
    kv.set('inventory-users', users),
    kv.set('inventory-roles', roles),
    kv.set('inventory-permissions', permissions),
    kv.set('inventory-faqs', faqs),
    kv.set('inventory-trade-in-policies', tradeInPolicies),
    kv.set('inventory-product-imeis', productImeis),
    kv.set('inventory-imei-history', imeiHistory),
    kv.set('inventory-stock-history', stockHistoryEntries)
  ])

  await kv.set('settings_last_snapshot_at', new Date().toISOString())

  return {
    profiles: profiles.length,
    salesProfiles: salesProfiles.length,
    locations: locations.length,
    products: products.length,
    stockEntries: stockRecords.length,
    orders: orderRecords.length,
    orderItems: orderItems.length,
    stockTransfers: stockTransfers.length,
    returns: returns.length,
    customers: customers.length,
    productImeis: productImeis.length,
    imeiHistoryEntries: imeiHistory.length,
    stockHistoryEntries: stockHistoryEntries.length
  }
}

function buildStockRecords(products: ProductWithStock[]): Stock[] {
  const stock: Stock[] = []
  for (const product of products) {
    if (!product.stock_items?.length) {
      continue
    }
    for (const item of product.stock_items) {
      const record: Stock = {
        id: typeof item.id === 'number' ? item.id : Number(`${product.id}${item.location_id ?? 0}`),
        product_id: product.id,
        location_id: item.location_id,
        cantidad_disponible: item.cantidad_disponible,
        cantidad_reservada: item.cantidad_reservada ?? 0,
        cantidad_defectuosa: item.cantidad_defectuosa ?? 0
      }
      stock.push(record)
    }
  }
  return stock
}

function flattenOrderItems(orders: OrderWithItems[]): OrderItem[] {
  const items: OrderItem[] = []
  for (const order of orders) {
    for (const item of order.items) {
      items.push({ ...item, order_id: order.id })
    }
  }
  return items
}

function flattenTradeIns(orders: OrderWithItems[]): TradeIn[] {
  const trades: TradeIn[] = []
  for (const order of orders) {
    if (!order.trade_ins?.length) {
      continue
    }
    for (const trade of order.trade_ins) {
      trades.push({ ...trade, order_id: trade.order_id ?? order.id })
    }
  }
  return trades
}

function extractFinancingOptions(banks: Bank[]): FinancingOption[] {
  const options: FinancingOption[] = []
  for (const bank of banks) {
    if (!Array.isArray(bank.financing_options)) {
      continue
    }
    for (const option of bank.financing_options) {
      options.push({
        ...option,
        bank_id: option.bank_id ?? bank.id
      })
    }
  }
  return options
}

async function collectStockHistorySnapshot(locations: Location[], days = 90): Promise<StockHistory[]> {
  if (!locations?.length) {
    return []
  }

  const limitPerLocation = 200
  const history: StockHistory[] = []

  for (const location of locations) {
    try {
      const entries = await apiClient.getLocationStockHistory(location.id, {
        limit: limitPerLocation,
        days
      })

      if (Array.isArray(entries) && entries.length) {
        history.push(...entries)
      }
    } catch (error) {
      console.warn(
        `[syncService] No se pudo obtener historial de stock para la ubicación ${location.id}.`,
        error
      )
    }
  }

  return history
}

async function safeFetch<T>(action: () => Promise<T>, fallback: T, label: string): Promise<T> {
  try {
    return await action()
  } catch (error) {
    console.warn(`[syncService] No se pudo obtener ${label} durante el snapshot.`, error)
    return fallback
  }
}
