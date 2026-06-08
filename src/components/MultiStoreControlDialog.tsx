import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { toast } from 'sonner'
import { CheckSquare, CreditCard, Database, Package, Plus, ShieldCheck, Trash, User as UserIcon } from '@phosphor-icons/react'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { calculateLuhnCheckDigit } from '@/lib/utils'
import type {
  AuditLogEntry,
  BankTransferReconciliationReport,
  InventoryCount,
  Location,
  LocationDailyClose,
  ProductIMEI,
  ProductWithStock,
  PurchaseReceipt,
  Supplier,
  User,
  UserLocationAccessInput,
} from '@/lib/types'

interface MultiStoreControlDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialTab?: string
  locations: Location[]
  products: ProductWithStock[]
  permissions: {
    canViewInventory: boolean
    canCountInventory: boolean
    canAdjustInventory: boolean
    canManagePurchases: boolean
    canManageCashCloses: boolean
    canManageLocationAccess: boolean
    canViewAudit: boolean
    canViewReports: boolean
  }
  onInventoryChanged?: () => Promise<void> | void
}

interface ReceiptLine {
  id: string
  product_id: string
  product_search: string
  quantity: string
  unit_cost: string
  imeis: string
  notes: string
}

interface CountLine {
  id: string
  product_id: string
  product_search: string
  counted_quantity: string
  imeis: string
  notes: string
}

interface ScannerMatch {
  imei: string
  status: 'ok' | 'other_location' | 'blocked' | 'unknown'
  product_id?: number
  product_name?: string
  location_name?: string
  detail?: string
}

interface ScannerProductSummary {
  product_id: number
  product_name: string
  sku?: string
  scan_source: 'imei' | 'sku'
  expected_quantity: number
  scanned_quantity: number
  difference: number
  scanned_imeis: string[]
}

const todayInputValue = () => new Date().toISOString().slice(0, 10)
const createLineId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`

const createReceiptLine = (productId = ''): ReceiptLine => ({
  id: createLineId(),
  product_id: productId,
  product_search: '',
  quantity: '1',
  unit_cost: '0',
  imeis: '',
  notes: '',
})

const createCountLine = (productId = ''): CountLine => ({
  id: createLineId(),
  product_id: productId,
  product_search: '',
  counted_quantity: '0',
  imeis: '',
  notes: '',
})

const normalizeScannerToken = (value: string) => {
  const trimmed = value.trim()
  const digits = trimmed.replace(/\D/g, '')

  if (digits.length === 14) {
    try {
      return `${digits}${calculateLuhnCheckDigit(digits)}`
    } catch {
      return digits
    }
  }

  if (digits.length === 15) {
    return digits
  }

  return trimmed.toUpperCase()
}

const parseScannerTokens = (value: string) => value
  .split(/[\n,;\t ]+/)
  .map(normalizeScannerToken)
  .filter(Boolean)

const isImeiToken = (value: string) => /^\d{15}$/.test(value)

const isAvailableImeiRecord = (record: ProductIMEI) => !record.vendido && !record.order_id && !record.transfer_id

const describeImeiState = (record: ProductIMEI) => {
  if (record.vendido) return 'ya fue vendido'
  if (record.transfer_id) return 'está en transferencia'
  if (record.order_id) return 'está reservado en una orden'
  return 'no está disponible'
}

const accessLabels: Record<keyof Omit<UserLocationAccessInput, 'location_id'>, string> = {
  can_view: 'Ver',
  can_edit: 'Editar stock',
  can_close_cash: 'Cerrar caja',
  can_count_stock: 'Conteo físico',
  can_receive_purchase: 'Recibir compras',
}

export function MultiStoreControlDialog({
  open,
  onOpenChange,
  initialTab,
  locations,
  products,
  permissions,
  onInventoryChanged,
}: MultiStoreControlDialogProps) {
  const activeLocations = useMemo(() => locations.filter(location => location.activo), [locations])
  const activeProducts = useMemo(() => products.filter(product => product.activo), [products])
  const firstProductId = activeProducts[0]?.id ? String(activeProducts[0].id) : ''

  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [receipts, setReceipts] = useState<PurchaseReceipt[]>([])
  const [counts, setCounts] = useState<InventoryCount[]>([])
  const [closes, setCloses] = useState<LocationDailyClose[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const [selectedLocationId, setSelectedLocationId] = useState<string>('')
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>('none')
  const [receiptInvoice, setReceiptInvoice] = useState('')
  const [receiptNotes, setReceiptNotes] = useState('')
  const [receiptLines, setReceiptLines] = useState<ReceiptLine[]>([createReceiptLine()])

  const [countLocationId, setCountLocationId] = useState<string>('')
  const [countNotes, setCountNotes] = useState('')
  const [countLines, setCountLines] = useState<CountLine[]>([createCountLine()])
  const [imeiInventory, setImeiInventory] = useState<ProductIMEI[]>([])
  const [scannerInput, setScannerInput] = useState('')
  const [scanEntry, setScanEntry] = useState('')
  const scannerInputRef = useRef<HTMLInputElement | null>(null)

  const [closeLocationId, setCloseLocationId] = useState<string>('')
  const [closeDate, setCloseDate] = useState(todayInputValue())
  const [cashCounted, setCashCounted] = useState('0')
  const [transferTotal, setTransferTotal] = useState('0')
  const [cardTotal, setCardTotal] = useState('0')
  const [financingTotal, setFinancingTotal] = useState('0')
  const [closeNotes, setCloseNotes] = useState('')

  const [accessUserId, setAccessUserId] = useState('')
  const [accessLocationId, setAccessLocationId] = useState<string>('')
  const [accessFlags, setAccessFlags] = useState({
    can_view: true,
    can_edit: false,
    can_close_cash: false,
    can_count_stock: false,
    can_receive_purchase: false,
  })
  const [auditLocationId, setAuditLocationId] = useState<string>('all')
  const [auditEntityType, setAuditEntityType] = useState('')
  const [auditAction, setAuditAction] = useState('')
  const [bankReport, setBankReport] = useState<BankTransferReconciliationReport | null>(null)
  const [activeTab, setActiveTab] = useState<string>('receipts')
  const [bankLocationId, setBankLocationId] = useState<string>('all')
  const [bankStartDate, setBankStartDate] = useState(todayInputValue())
  const [bankEndDate, setBankEndDate] = useState(todayInputValue())
  const [bankNameFilter, setBankNameFilter] = useState('')

  const closeSummary = useMemo(() => {
    return closes.reduce(
      (summary, close) => {
        const difference = Number(close.difference || 0)
        summary.totalDifference += difference
        if (difference !== 0) summary.withDifference += 1
        return summary
      },
      { totalDifference: 0, withDifference: 0 }
    )
  }, [closes])

  const paymentDifference = (close: LocationDailyClose) => ({
    efectivo: Number(close.cash_counted || 0) - Number(close.cash_expected || 0),
    transferencia: Number(close.transfer_total || 0) - Number(close.transfer_expected || 0),
    tarjeta: Number(close.card_total || 0) - Number(close.card_expected || 0),
    financiamiento: Number(close.financing_total || 0) - Number(close.financing_expected || 0),
  })

  const countSummary = useMemo(() => {
    return counts.reduce(
      (summary, count) => {
        const difference = count.items.reduce((total, item) => total + Number(item.difference || 0), 0)
        summary.totalDifference += difference
        if (count.status === 'draft') summary.pending += 1
        return summary
      },
      { totalDifference: 0, pending: 0 }
    )
  }, [counts])

  const countLocationNumber = countLocationId ? Number(countLocationId) : undefined

  const scannedCodes = useMemo(() => parseScannerTokens(scannerInput), [scannerInput])
  const scannedImeis = useMemo(() => scannedCodes.filter(isImeiToken), [scannedCodes])
  const scannedSkuCodes = useMemo(() => scannedCodes.filter(code => !isImeiToken(code)), [scannedCodes])

  const duplicateScannedImeis = useMemo(() => {
    const seen = new Set<string>()
    const duplicates = new Set<string>()

    for (const imei of scannedImeis) {
      if (seen.has(imei)) {
        duplicates.add(imei)
      } else {
        seen.add(imei)
      }
    }

    return Array.from(duplicates)
  }, [scannedImeis])

  const productBySku = useMemo(() => {
    return activeProducts.reduce((map, product) => {
      if (product.sku) {
        map.set(product.sku.trim().toUpperCase(), product)
      }
      return map
    }, new Map<string, ProductWithStock>())
  }, [activeProducts])

  const scannerAnalysis = useMemo(() => {
    if (!countLocationNumber) {
      return {
        expectedTotal: 0,
        matchedTotal: 0,
        missingTotal: 0,
        duplicateImeis: duplicateScannedImeis,
        wrongLocation: [] as ScannerMatch[],
        blocked: [] as ScannerMatch[],
        unknown: [] as ScannerMatch[],
        missingImeis: [] as ProductIMEI[],
        missingSkuSummaries: [] as ScannerProductSummary[],
        productSummaries: [] as ScannerProductSummary[],
      }
    }

    const serializedProducts = new Map(
      activeProducts
        .filter(product => product.is_serialized)
        .map(product => [product.id, product])
    )
    const nonSerializedProducts = new Map(
      activeProducts
        .filter(product => !product.is_serialized)
        .map(product => [product.id, product])
    )

    const groupedByImei = imeiInventory.reduce((map, record) => {
      const current = map.get(record.imei) || []
      current.push(record)
      map.set(record.imei, current)
      return map
    }, new Map<string, ProductIMEI[]>())

    const uniqueScanned = Array.from(new Set(scannedImeis))
    const matches = uniqueScanned.map<ScannerMatch>(imei => {
      const records = groupedByImei.get(imei) || []
      const localAvailable = records.find(record => record.location_id === countLocationNumber && isAvailableImeiRecord(record))
      if (localAvailable) {
        return {
          imei,
          status: 'ok',
          product_id: localAvailable.product_id,
          product_name: localAvailable.product_name,
          location_name: localAvailable.location_name,
        }
      }

      const localBlocked = records.find(record => record.location_id === countLocationNumber)
      if (localBlocked) {
        return {
          imei,
          status: 'blocked',
          product_id: localBlocked.product_id,
          product_name: localBlocked.product_name,
          location_name: localBlocked.location_name,
          detail: describeImeiState(localBlocked),
        }
      }

      const otherAvailable = records.find(record => isAvailableImeiRecord(record))
      if (otherAvailable) {
        return {
          imei,
          status: 'other_location',
          product_id: otherAvailable.product_id,
          product_name: otherAvailable.product_name,
          location_name: otherAvailable.location_name,
          detail: `pertenece a ${otherAvailable.location_name || `ubicación #${otherAvailable.location_id}`}`,
        }
      }

      const blockedRecord = records[0]
      if (blockedRecord) {
        return {
          imei,
          status: 'blocked',
          product_id: blockedRecord.product_id,
          product_name: blockedRecord.product_name,
          location_name: blockedRecord.location_name,
          detail: describeImeiState(blockedRecord),
        }
      }

      return { imei, status: 'unknown', detail: 'no existe en el sistema' }
    })

    const okMatches = matches.filter(match => match.status === 'ok')
    const expectedImeis = imeiInventory.filter(record => (
      record.location_id === countLocationNumber &&
      isAvailableImeiRecord(record) &&
      serializedProducts.has(record.product_id)
    ))

    const scannedOkSet = new Set(okMatches.map(match => match.imei))
    const missingImeis = expectedImeis.filter(record => !scannedOkSet.has(record.imei))

    const expectedByProduct = expectedImeis.reduce((map, record) => {
      map.set(record.product_id, (map.get(record.product_id) || 0) + 1)
      return map
    }, new Map<number, number>())

    const scannedByProduct = okMatches.reduce((map, match) => {
      if (!match.product_id) return map
      const current = map.get(match.product_id) || []
      current.push(match.imei)
      map.set(match.product_id, current)
      return map
    }, new Map<number, string[]>())

    const imeiProductIds = Array.from(new Set([...expectedByProduct.keys(), ...scannedByProduct.keys()]))
    const imeiProductSummaries = imeiProductIds
      .map<ScannerProductSummary>(productId => {
        const product = serializedProducts.get(productId)
        const scannedForProduct = scannedByProduct.get(productId) || []
        const expectedQuantity = expectedByProduct.get(productId) || 0
        return {
          product_id: productId,
          product_name: product?.nombre || `Producto #${productId}`,
          sku: product?.sku,
          scan_source: 'imei',
          expected_quantity: expectedQuantity,
          scanned_quantity: scannedForProduct.length,
          difference: scannedForProduct.length - expectedQuantity,
          scanned_imeis: scannedForProduct,
        }
      })

    const scannedSkuByProduct = new Map<number, number>()
    const unknownSkuMatches: ScannerMatch[] = []

    for (const code of scannedSkuCodes) {
      const product = productBySku.get(code)
      if (!product) {
        unknownSkuMatches.push({ imei: code, status: 'unknown', detail: 'SKU/código no existe en el sistema' })
        continue
      }

      if (product.is_serialized) {
        unknownSkuMatches.push({
          imei: code,
          status: 'unknown',
          product_id: product.id,
          product_name: product.nombre,
          detail: 'SKU de producto serializado; escanee cada IMEI para validar ubicación',
        })
        continue
      }

      scannedSkuByProduct.set(product.id, (scannedSkuByProduct.get(product.id) || 0) + 1)
    }

    const expectedSkuByProduct = new Map<number, number>()
    if (scannedSkuCodes.length > 0) {
      for (const product of nonSerializedProducts.values()) {
        const stockItem = product.stock_items?.find(item => item.location_id === countLocationNumber)
        const expectedQuantity = Number(stockItem?.cantidad_disponible || 0)
        if (expectedQuantity > 0 || scannedSkuByProduct.has(product.id)) {
          expectedSkuByProduct.set(product.id, expectedQuantity)
        }
      }
    }

    const skuProductIds = Array.from(new Set([...expectedSkuByProduct.keys(), ...scannedSkuByProduct.keys()]))
    const skuProductSummaries = skuProductIds.map<ScannerProductSummary>(productId => {
      const product = nonSerializedProducts.get(productId)
      const expectedQuantity = expectedSkuByProduct.get(productId) || 0
      const scannedQuantity = scannedSkuByProduct.get(productId) || 0
      return {
        product_id: productId,
        product_name: product?.nombre || `Producto #${productId}`,
        sku: product?.sku,
        scan_source: 'sku',
        expected_quantity: expectedQuantity,
        scanned_quantity: scannedQuantity,
        difference: scannedQuantity - expectedQuantity,
        scanned_imeis: [],
      }
    })

    const productSummaries = [...imeiProductSummaries, ...skuProductSummaries]
      .sort((a, b) => {
        const differenceDelta = Math.abs(b.difference) - Math.abs(a.difference)
        if (differenceDelta !== 0) return differenceDelta
        return a.product_name.localeCompare(b.product_name)
      })

    const expectedSkuTotal = Array.from(expectedSkuByProduct.values()).reduce((total, value) => total + value, 0)
    const scannedSkuTotal = Array.from(scannedSkuByProduct.values()).reduce((total, value) => total + value, 0)
    const missingSkuTotal = skuProductSummaries.reduce((total, summary) => total + Math.max(0, -summary.difference), 0)

    return {
      expectedTotal: expectedImeis.length + expectedSkuTotal,
      matchedTotal: okMatches.length + scannedSkuTotal,
      missingTotal: missingImeis.length + missingSkuTotal,
      duplicateImeis: duplicateScannedImeis,
      wrongLocation: matches.filter(match => match.status === 'other_location'),
      blocked: matches.filter(match => match.status === 'blocked'),
      unknown: [...matches.filter(match => match.status === 'unknown'), ...unknownSkuMatches],
      missingImeis,
      missingSkuSummaries: skuProductSummaries.filter(summary => summary.difference < 0),
      productSummaries,
    }
  }, [activeProducts, countLocationNumber, duplicateScannedImeis, imeiInventory, productBySku, scannedImeis, scannedSkuCodes])

  const availableTabs = useMemo(() => {
    const tabs: string[] = []
    if (permissions.canViewInventory || permissions.canManagePurchases) tabs.push('receipts')
    if (permissions.canViewInventory || permissions.canCountInventory || permissions.canAdjustInventory) tabs.push('counts')
    if (permissions.canManageCashCloses) tabs.push('closes')
    if (permissions.canViewReports) tabs.push('bank')
    if (permissions.canManageLocationAccess) tabs.push('access')
    if (permissions.canViewAudit) tabs.push('audit')
    return tabs
  }, [permissions])

  const loadData = useCallback(async () => {
    if (!open) return
    setLoading(true)
    try {
      const [supplierResult, receiptResult, countResult, closeResult, auditResult, imeiResult] = await Promise.allSettled([
        permissions.canViewInventory ? inventoryServiceInstance.listSuppliers(false) : Promise.resolve([]),
        permissions.canViewInventory ? inventoryServiceInstance.listPurchaseReceipts({ limit: 20 }) : Promise.resolve([]),
        (permissions.canViewInventory || permissions.canCountInventory || permissions.canAdjustInventory)
          ? inventoryServiceInstance.listInventoryCounts({ limit: 20 })
          : Promise.resolve([]),
        permissions.canManageCashCloses ? inventoryServiceInstance.listLocationDailyCloses({ limit: 20 }) : Promise.resolve([]),
        permissions.canViewAudit ? inventoryServiceInstance.listAuditLogs({ limit: 40 }) : Promise.resolve([]),
        (permissions.canViewInventory || permissions.canCountInventory || permissions.canAdjustInventory)
          ? inventoryServiceInstance.listProductIMEIs()
          : Promise.resolve([]),
      ])

      setSuppliers(supplierResult.status === 'fulfilled' ? supplierResult.value : [])
      setReceipts(receiptResult.status === 'fulfilled' ? receiptResult.value : [])
      setCounts(countResult.status === 'fulfilled' ? countResult.value : [])
      setCloses(closeResult.status === 'fulfilled' ? closeResult.value : [])
      setAuditLogs(auditResult.status === 'fulfilled' ? auditResult.value : [])
      setImeiInventory(imeiResult.status === 'fulfilled' ? imeiResult.value : [])

      const failedSections = [
        supplierResult.status === 'rejected' ? 'proveedores' : null,
        receiptResult.status === 'rejected' ? 'recepciones' : null,
        countResult.status === 'rejected' ? 'conteos' : null,
        closeResult.status === 'rejected' ? 'cierres' : null,
        auditResult.status === 'rejected' ? 'auditoría' : null,
        imeiResult.status === 'rejected' ? 'imeis' : null,
      ].filter(Boolean)

      if (failedSections.length > 0) {
        console.warn('Secciones no disponibles en control multitienda:', failedSections)
      }

      if (permissions.canManageLocationAccess) {
        try {
          setUsers(await inventoryServiceInstance.listUsers())
        } catch (error) {
          console.warn('No se pudieron cargar usuarios para accesos por ubicación:', error)
          setUsers([])
        }
      } else {
        setUsers([])
      }
    } catch (error) {
      console.error('Error loading multistore control data:', error)
      toast.error('Error al cargar control multitienda')
    } finally {
      setLoading(false)
    }
  }, [open, permissions])

  useEffect(() => {
    if (open) {
      const firstLocationId = activeLocations[0]?.id ? String(activeLocations[0].id) : ''
      setSelectedLocationId(firstLocationId)
      setCountLocationId(firstLocationId)
      setCloseLocationId(firstLocationId)
      setAccessLocationId(firstLocationId)
      setReceiptLines([createReceiptLine(firstProductId)])
      setCountLines([createCountLine(firstProductId)])
      setScannerInput('')
      setScanEntry('')
      setActiveTab(() => {
        if (initialTab && availableTabs.includes(initialTab)) {
          return initialTab
        }
        return availableTabs[0] || 'receipts'
      })
      loadData()
    }
  }, [open, activeLocations, firstProductId, availableTabs, initialTab, loadData])

  const handleApplyAuditFilters = async () => {
    setLoading(true)
    try {
      const filters = {
        location_id: auditLocationId !== 'all' ? Number(auditLocationId) : undefined,
        entity_type: auditEntityType.trim() || undefined,
        action: auditAction.trim() || undefined,
        limit: 100,
      }
      setAuditLogs(await inventoryServiceInstance.listAuditLogs(filters))
    } catch (error) {
      console.error('Error loading audit logs:', error)
      toast.error('No se pudo cargar la bitácora con esos filtros')
    } finally {
      setLoading(false)
    }
  }

  const loadBankReconciliation = async () => {
    setLoading(true)
    try {
      const report = await inventoryServiceInstance.getBankTransferReconciliation({
        start_date: bankStartDate || undefined,
        end_date: bankEndDate || undefined,
        location_id: bankLocationId !== 'all' ? Number(bankLocationId) : undefined,
        bank_name: bankNameFilter.trim() || undefined,
      })
      setBankReport(report)
    } catch (error) {
      console.error('Error loading bank reconciliation:', error)
      toast.error('No se pudo cargar la conciliación bancaria')
    } finally {
      setLoading(false)
    }
  }

  const exportBankReconciliationCsv = () => {
    const rows = [
      ['Orden', 'Fecha', 'Cliente', 'Teléfono', 'Ubicación', 'Banco', 'Referencia', 'Estado', 'Validado por', 'Total'],
      ...(bankReport?.items || []).map(item => [
        String(item.order_id),
        new Date(item.created_at).toLocaleString('es-HN'),
        item.customer_name || '',
        item.customer_phone || '',
        item.location_nombre || locationName(item.location_id),
        item.bank_name || '',
        item.reference || '',
        item.estado,
        item.validated_by || '',
        String(Number(item.total || 0)),
      ]),
    ]
    const escapeCsv = (value: string) => {
      if (value.includes(',') || value.includes('"') || value.includes('\n')) {
        return `"${value.replace(/"/g, '""')}"`
      }
      return value
    }
    const csv = rows.map(row => row.map(escapeCsv).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `conciliacion_transferencias_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const locationName = (id?: number) => locations.find(location => location.id === id)?.nombre || `Ubicación #${id}`
  const productName = (id?: number) => products.find(product => product.id === id)?.nombre || `Producto #${id}`
  const userName = (user: User) => user.full_name || user.username || `Usuario #${user.id}`

  const productSearchText = (product: ProductWithStock) => [
    product.nombre,
    product.sku,
    product.marca,
    product.modelo,
    product.color,
    product.capacidad,
  ].filter(Boolean).join(' ').toLowerCase()

  const filteredProductsForSearch = (search: string, selectedProductId?: string) => {
    const tokens = search.trim().toLowerCase().split(/\s+/).filter(Boolean)
    const selectedProduct = activeProducts.find(product => String(product.id) === selectedProductId)
    const matches = activeProducts.filter(product => {
      if (tokens.length === 0) return true
      const haystack = productSearchText(product)
      return tokens.every(token => haystack.includes(token))
    })

    const deduped = new Map<number, ProductWithStock>()
    if (selectedProduct) deduped.set(selectedProduct.id, selectedProduct)
    matches.slice(0, 12).forEach(product => deduped.set(product.id, product))
    return Array.from(deduped.values())
  }

  const selectReceiptProduct = (lineId: string, product: ProductWithStock) => {
    updateReceiptLine(lineId, { product_id: String(product.id), product_search: product.nombre })
  }

  const selectCountProduct = (lineId: string, product: ProductWithStock) => {
    updateCountLine(lineId, { product_id: String(product.id), product_search: product.nombre })
  }

  const updateReceiptLine = (lineId: string, updates: Partial<ReceiptLine>) => {
    setReceiptLines(current => current.map(line => line.id === lineId ? { ...line, ...updates } : line))
  }

  const updateCountLine = (lineId: string, updates: Partial<CountLine>) => {
    setCountLines(current => current.map(line => line.id === lineId ? { ...line, ...updates } : line))
  }

  const appendScannerTokens = useCallback((value: string) => {
    if (!countLocationId) {
      toast.error('Seleccione ubicación antes de escanear')
      return
    }

    const tokens = parseScannerTokens(value)
    if (!tokens.length) {
      toast.error('Escanee o escriba un IMEI/SKU válido')
      return
    }

    const existingImeis = new Set(scannedImeis)
    const acceptedTokens: string[] = []
    const duplicatedImeis: string[] = []

    for (const token of tokens) {
      if (isImeiToken(token) && existingImeis.has(token)) {
        duplicatedImeis.push(token)
        continue
      }

      if (isImeiToken(token)) {
        existingImeis.add(token)
      }
      acceptedTokens.push(token)
    }

    if (acceptedTokens.length) {
      setScannerInput(current => [current.trim(), ...acceptedTokens].filter(Boolean).join('\n'))
    }

    if (duplicatedImeis.length) {
      toast.error(`${duplicatedImeis.length} IMEI(s) ya estaban escaneados`)
    }

    setScanEntry('')
    requestAnimationFrame(() => scannerInputRef.current?.focus())
  }, [countLocationId, scannedImeis])

  const handleScannerKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'Enter') return
    event.preventDefault()
    appendScannerTokens(scanEntry)
  }

  const handleCreateReceipt = async () => {
    if (!selectedLocationId) {
      toast.error('Seleccione ubicación')
      return
    }

    const items = receiptLines.map(line => {
      const imeis = line.imeis
        .split(/\n|,/)
        .map(imei => imei.trim())
        .filter(Boolean)

      return {
        product_id: Number(line.product_id),
        quantity: Number(line.quantity),
        unit_cost: Number(line.unit_cost || 0),
        imeis: imeis.length ? imeis : undefined,
        notes: line.notes.trim() || undefined,
      }
    })

    if (items.some(item => !item.product_id || item.quantity < 1 || item.unit_cost < 0)) {
      toast.error('Revise producto, cantidad y costo en cada línea')
      return
    }

    setSubmitting(true)
    try {
      await inventoryServiceInstance.createPurchaseReceipt({
        supplier_id: selectedSupplierId !== 'none' ? Number(selectedSupplierId) : undefined,
        location_id: Number(selectedLocationId),
        invoice_number: receiptInvoice.trim() || undefined,
        notes: receiptNotes.trim() || undefined,
        items,
      })
      toast.success(`Recepción registrada con ${items.length} producto(s)`)
      setReceiptInvoice('')
      setReceiptNotes('')
      setReceiptLines([createReceiptLine(firstProductId)])
      await loadData()
      await onInventoryChanged?.()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al registrar recepción')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCreateCount = async () => {
    if (!countLocationId) {
      toast.error('Seleccione ubicación')
      return
    }

    const items = countLines.map(line => {
      const imeis = parseScannerTokens(line.imeis).filter(isImeiToken)
      return {
        product_id: Number(line.product_id),
        counted_quantity: imeis.length ? imeis.length : Number(line.counted_quantity),
        imeis,
        notes: line.notes.trim() || undefined,
      }
    })

    if (items.some(item => !item.product_id || item.counted_quantity < 0)) {
      toast.error('Revise producto y cantidad física en cada línea')
      return
    }

    const scannerNotes = scannerInput.trim()
      ? [
          `Escaneo físico ${locationName(Number(countLocationId))}: sistema ${scannerAnalysis.expectedTotal}, escaneado ${scannerAnalysis.matchedTotal}, faltantes ${scannerAnalysis.missingTotal}, otra ubicación ${scannerAnalysis.wrongLocation.length}, bloqueados ${scannerAnalysis.blocked.length}, desconocidos ${scannerAnalysis.unknown.length}, duplicados ${scannerAnalysis.duplicateImeis.length}.`,
          scannerAnalysis.wrongLocation.length ? `Otra ubicación: ${scannerAnalysis.wrongLocation.slice(0, 20).map(item => `${item.imei} (${item.location_name || item.detail || 'sin ubicación'})`).join(', ')}` : '',
          scannerAnalysis.blocked.length ? `Bloqueados: ${scannerAnalysis.blocked.slice(0, 20).map(item => `${item.imei} (${item.detail || 'no disponible'})`).join(', ')}` : '',
          scannerAnalysis.unknown.length ? `Desconocidos/SKU inválidos: ${scannerAnalysis.unknown.slice(0, 20).map(item => item.imei).join(', ')}` : '',
        ].filter(Boolean).join('\n')
      : ''
    const combinedNotes = [countNotes.trim(), scannerNotes].filter(Boolean).join('\n\n')

    setSubmitting(true)
    try {
      await inventoryServiceInstance.createInventoryCount({
        location_id: Number(countLocationId),
        notes: combinedNotes || undefined,
        items,
      })
      toast.success(`Conteo creado con ${items.length} producto(s)`)
      setCountNotes('')
      setCountLines([createCountLine(firstProductId)])
      setScannerInput('')
      setScanEntry('')
      await loadData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al crear conteo')
    } finally {
      setSubmitting(false)
    }
  }

  const handleApplyScannerToCount = () => {
    if (!countLocationNumber) {
      toast.error('Seleccione ubicación para aplicar el escaneo')
      return
    }

    const generatedLines = scannerAnalysis.productSummaries
      .filter(summary => summary.expected_quantity > 0 || summary.scanned_quantity > 0)
      .map<CountLine>(summary => ({
        id: createLineId(),
        product_id: String(summary.product_id),
        product_search: summary.product_name,
        counted_quantity: String(summary.scanned_quantity),
        imeis: summary.scanned_imeis.join('\n'),
        notes: summary.difference === 0
          ? `Conteo generado desde escaneo por ${summary.scan_source === 'imei' ? 'IMEI' : 'SKU'}`
          : `Escaneo por ${summary.scan_source === 'imei' ? 'IMEI' : 'SKU'}: sistema ${summary.expected_quantity}, físico ${summary.scanned_quantity}`,
      }))

    if (!generatedLines.length) {
      toast.error('No hay IMEIs válidos para convertir en líneas de conteo')
      return
    }

    setCountLines(current => {
      const generatedProductIds = new Set(generatedLines.map(line => Number(line.product_id)))
      const manualLines = current.filter(line => !generatedProductIds.has(Number(line.product_id)))
      return [...manualLines, ...generatedLines]
    })

    toast.success(`Escaneo aplicado: ${generatedLines.length} producto(s) preparados para el conteo`)
  }

  const handleApproveCount = async (countId: number) => {
    setSubmitting(true)
    try {
      await inventoryServiceInstance.approveInventoryCount(countId, 'Aprobado desde control multitienda')
      toast.success('Conteo aprobado y stock ajustado')
      await loadData()
      await onInventoryChanged?.()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al aprobar conteo')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCreateClose = async () => {
    if (!closeLocationId) {
      toast.error('Seleccione ubicación')
      return
    }

    setSubmitting(true)
    try {
      await inventoryServiceInstance.createLocationDailyClose({
        location_id: Number(closeLocationId),
        close_date: new Date(`${closeDate}T12:00:00`).toISOString(),
        cash_counted: Number(cashCounted || 0),
        transfer_total: Number(transferTotal || 0),
        card_total: Number(cardTotal || 0),
        financing_total: Number(financingTotal || 0),
        notes: closeNotes.trim() || undefined,
      })
      toast.success('Cierre por tienda registrado')
      setCloseNotes('')
      await loadData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al registrar cierre')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSaveAccess = async () => {
    if (!accessUserId || !accessLocationId) {
      toast.error('Seleccione usuario y ubicación')
      return
    }

    const selectedAccess: UserLocationAccessInput = {
      location_id: Number(accessLocationId),
      ...accessFlags,
    }

    setSubmitting(true)
    try {
      const existingAccess = await inventoryServiceInstance.listUserLocationAccess(Number(accessUserId))
      const payload: UserLocationAccessInput[] = [
        ...existingAccess
          .filter(access => access.location_id !== selectedAccess.location_id)
          .map(access => ({
            location_id: access.location_id,
            can_view: access.can_view,
            can_edit: access.can_edit,
            can_close_cash: access.can_close_cash,
            can_count_stock: access.can_count_stock,
            can_receive_purchase: access.can_receive_purchase,
          })),
        selectedAccess,
      ]
      await inventoryServiceInstance.replaceUserLocationAccess(Number(accessUserId), payload)
      toast.success('Acceso por ubicación actualizado')
      await loadData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al guardar acceso')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck size={22} weight="fill" className="text-emerald-600" />
            Control Multitienda
          </DialogTitle>
          <DialogDescription>
            Conteos físicos, recepciones, cierres por tienda, accesos y auditoría operativa.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="min-h-0 flex-1 flex flex-col">
          <TabsList className="grid grid-cols-6 w-full">
            {availableTabs.includes('receipts') && <TabsTrigger value="receipts"><Package size={16} className="mr-1" />Recepción</TabsTrigger>}
            {availableTabs.includes('counts') && <TabsTrigger value="counts"><CheckSquare size={16} className="mr-1" />Conteos</TabsTrigger>}
            {availableTabs.includes('closes') && <TabsTrigger value="closes"><CreditCard size={16} className="mr-1" />Caja</TabsTrigger>}
            {availableTabs.includes('bank') && <TabsTrigger value="bank"><CreditCard size={16} className="mr-1" />Banco</TabsTrigger>}
            {availableTabs.includes('access') && <TabsTrigger value="access"><ShieldCheck size={16} className="mr-1" />Accesos</TabsTrigger>}
            {availableTabs.includes('audit') && <TabsTrigger value="audit"><Database size={16} className="mr-1" />Auditoría</TabsTrigger>}
          </TabsList>

          <ScrollArea className="flex-1 mt-4 pr-3">
            {loading && <p className="text-sm text-muted-foreground py-4">Cargando control multitienda...</p>}
            {!loading && availableTabs.length === 0 && (
              <p className="text-sm text-muted-foreground py-4">Tu rol no tiene permisos para usar este módulo.</p>
            )}

            <TabsContent value="receipts" className="space-y-4 mt-0">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label>Ubicación</Label>
                  <Select value={selectedLocationId} onValueChange={setSelectedLocationId}>
                    <SelectTrigger><SelectValue placeholder="Ubicación" /></SelectTrigger>
                    <SelectContent>{activeLocations.map(location => <SelectItem key={location.id} value={String(location.id)}>{location.nombre}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Proveedor</Label>
                  <Select value={selectedSupplierId} onValueChange={setSelectedSupplierId}>
                    <SelectTrigger><SelectValue placeholder="Proveedor" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Sin proveedor</SelectItem>
                      {suppliers.map(supplier => <SelectItem key={supplier.id} value={String(supplier.id)}>{supplier.nombre}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Factura</Label>
                  <Input value={receiptInvoice} onChange={event => setReceiptInvoice(event.target.value)} placeholder="FAC-001" />
                </div>
              </div>

              <Card className="p-3">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <h3 className="font-medium">Productos recibidos</h3>
                  <Button size="sm" variant="outline" onClick={() => setReceiptLines(current => [...current, createReceiptLine(firstProductId)])}>
                    <Plus size={16} className="mr-2" />Agregar línea
                  </Button>
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Producto</TableHead>
                      <TableHead className="w-24">Cantidad</TableHead>
                      <TableHead className="w-32">Costo</TableHead>
                      <TableHead>IMEIs</TableHead>
                      <TableHead>Notas</TableHead>
                      <TableHead className="w-12" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {receiptLines.map(line => {
                      const receiptProductMatches = filteredProductsForSearch(line.product_search, line.product_id)
                      return (
                      <TableRow key={line.id}>
                        <TableCell className="min-w-56">
                          <div className="space-y-1.5">
                            <Input
                              value={line.product_search}
                              onChange={event => updateReceiptLine(line.id, { product_search: event.target.value, product_id: '' })}
                              placeholder="Buscar producto, SKU o modelo"
                            />
                            <div className="max-h-28 overflow-y-auto rounded-md border bg-background p-1">
                              {receiptProductMatches.length === 0 ? (
                                <p className="px-2 py-1.5 text-xs text-muted-foreground">Sin coincidencias</p>
                              ) : receiptProductMatches.map(product => (
                                <button
                                  key={product.id}
                                  type="button"
                                  className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-xs hover:bg-muted"
                                  onClick={() => selectReceiptProduct(line.id, product)}
                                >
                                  <span className="min-w-0 truncate">{product.nombre}</span>
                                  <Badge variant="secondary" className="shrink-0">{product.sku || 'Sin SKU'}</Badge>
                                </button>
                              ))}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell><Input type="number" min="1" value={line.quantity} onChange={event => updateReceiptLine(line.id, { quantity: event.target.value })} /></TableCell>
                        <TableCell><Input type="number" min="0" step="0.01" value={line.unit_cost} onChange={event => updateReceiptLine(line.id, { unit_cost: event.target.value })} /></TableCell>
                        <TableCell><Input value={line.imeis} onChange={event => updateReceiptLine(line.id, { imeis: event.target.value })} placeholder="IMEI1, IMEI2" /></TableCell>
                        <TableCell><Input value={line.notes} onChange={event => updateReceiptLine(line.id, { notes: event.target.value })} placeholder="Opcional" /></TableCell>
                        <TableCell>
                          <Button variant="ghost" size="icon" disabled={receiptLines.length === 1} onClick={() => setReceiptLines(current => current.filter(item => item.id !== line.id))}>
                            <Trash size={16} />
                          </Button>
                        </TableCell>
                      </TableRow>
                    )})}
                  </TableBody>
                </Table>
              </Card>

              {permissions.canManagePurchases && (
                <>
                  <Textarea value={receiptNotes} onChange={event => setReceiptNotes(event.target.value)} placeholder="Notas generales de recepción" rows={2} />
                  <Button onClick={handleCreateReceipt} disabled={submitting}><Package size={16} className="mr-2" />Registrar recepción</Button>
                </>
              )}

              <div className="space-y-2">
                {receipts.map(receipt => (
                  <Card key={receipt.id} className="p-3 flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">#{receipt.id} · {locationName(receipt.location_id)} · {receipt.invoice_number || 'Sin factura'}</p>
                      <p className="text-sm text-muted-foreground">{receipt.items?.length || 0} item(s) · Total {Number(receipt.total_cost).toLocaleString('es-HN', { minimumFractionDigits: 2 })}</p>
                    </div>
                    <Badge variant="outline">{receipt.status}</Badge>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="counts" className="space-y-4 mt-0">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground">Conteos pendientes</p>
                  <p className="text-2xl font-semibold">{countSummary.pending}</p>
                </Card>
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground">Diferencia neta reciente</p>
                  <p className="text-2xl font-semibold">{countSummary.totalDifference >= 0 ? '+' : ''}{countSummary.totalDifference}</p>
                </Card>
                <div className="space-y-1.5">
                  <Label>Ubicación</Label>
                  <Select value={countLocationId} onValueChange={value => {
                    setCountLocationId(value)
                    setScannerInput('')
                    setScanEntry('')
                  }}>
                    <SelectTrigger><SelectValue placeholder="Ubicación" /></SelectTrigger>
                    <SelectContent>{activeLocations.map(location => <SelectItem key={location.id} value={String(location.id)}>{location.nombre}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>

              <Card className="p-4 space-y-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h3 className="font-medium">Escaneo físico IMEI/SKU</h3>
                    <p className="text-sm text-muted-foreground">
                      Escanee celulares por IMEI y accesorios por SKU para conciliar físico vs sistema antes de crear el conteo.
                    </p>
                  </div>
                  <Button type="button" variant="outline" onClick={handleApplyScannerToCount} disabled={!scannerAnalysis.productSummaries.length}>
                    Cargar escaneo al conteo
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_auto] gap-2 items-end">
                  <div className="space-y-1.5">
                    <Label>Captura rápida</Label>
                    <Input
                      ref={scannerInputRef}
                      value={scanEntry}
                      onChange={event => setScanEntry(event.target.value)}
                      onKeyDown={handleScannerKeyDown}
                      placeholder="IMEI o SKU"
                      autoComplete="off"
                    />
                  </div>
                  <Button type="button" variant="secondary" onClick={() => appendScannerTokens(scanEntry)}>
                    Agregar
                  </Button>
                  <Button type="button" variant="outline" onClick={() => {
                    setScannerInput('')
                    setScanEntry('')
                    requestAnimationFrame(() => scannerInputRef.current?.focus())
                  }}>
                    Limpiar
                  </Button>
                </div>

                <div className="space-y-1.5">
                  <Label>Lecturas acumuladas</Label>
                  <Textarea
                    value={scannerInput}
                    onChange={event => setScannerInput(event.target.value)}
                    placeholder="Un IMEI o SKU por línea"
                    rows={6}
                  />
                </div>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <Card className="p-3">
                    <p className="text-xs text-muted-foreground">Esperados en sistema</p>
                    <p className="text-2xl font-semibold">{scannerAnalysis.expectedTotal}</p>
                  </Card>
                  <Card className="p-3">
                    <p className="text-xs text-muted-foreground">Escaneados válidos</p>
                    <p className="text-2xl font-semibold">{scannerAnalysis.matchedTotal}</p>
                  </Card>
                  <Card className="p-3">
                    <p className="text-xs text-muted-foreground">Faltantes</p>
                    <p className="text-2xl font-semibold">{scannerAnalysis.missingTotal}</p>
                  </Card>
                  <Card className="p-3">
                    <p className="text-xs text-muted-foreground">En otra ubicación</p>
                    <p className="text-2xl font-semibold">{scannerAnalysis.wrongLocation.length}</p>
                  </Card>
                  <Card className="p-3">
                    <p className="text-xs text-muted-foreground">Duplicados o inválidos</p>
                    <p className="text-2xl font-semibold">{scannerAnalysis.duplicateImeis.length + scannerAnalysis.unknown.length}</p>
                  </Card>
                </div>

                {!!scannerAnalysis.productSummaries.length && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-3">
                      <h4 className="text-sm font-medium">Resumen por producto</h4>
                      <span className="text-xs text-muted-foreground">IMEIs por ubicación y SKUs contra stock físico esperado</span>
                    </div>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Producto</TableHead>
                          <TableHead>Lectura</TableHead>
                          <TableHead className="text-right">Sistema</TableHead>
                          <TableHead className="text-right">Escaneado</TableHead>
                          <TableHead className="text-right">Diferencia</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {scannerAnalysis.productSummaries.map(summary => (
                          <TableRow key={summary.product_id}>
                            <TableCell>{summary.product_name}{summary.sku ? <span className="block text-xs text-muted-foreground">{summary.sku}</span> : null}</TableCell>
                            <TableCell><Badge variant="outline">{summary.scan_source === 'imei' ? 'IMEI' : 'SKU'}</Badge></TableCell>
                            <TableCell className="text-right">{summary.expected_quantity}</TableCell>
                            <TableCell className="text-right">{summary.scanned_quantity}</TableCell>
                            <TableCell className={`text-right ${summary.difference === 0 ? 'text-muted-foreground' : 'font-medium text-destructive'}`}>
                              {summary.difference > 0 ? '+' : ''}{summary.difference}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                  <Card className="p-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">Faltantes</p>
                      <Badge variant="outline">{scannerAnalysis.missingTotal}</Badge>
                    </div>
                    <div className="text-xs text-muted-foreground space-y-1 max-h-40 overflow-auto">
                      {scannerAnalysis.missingImeis.slice(0, 12).map(item => (
                        <p key={`${item.product_id}-${item.imei}`}>{item.imei} · {item.product_name || productName(item.product_id)}</p>
                      ))}
                      {scannerAnalysis.missingSkuSummaries.slice(0, 8).map(item => (
                        <p key={`sku-missing-${item.product_id}`}>{item.product_name} · faltan {Math.abs(item.difference)} unidad(es)</p>
                      ))}
                      {!scannerAnalysis.missingImeis.length && !scannerAnalysis.missingSkuSummaries.length && <p>No hay faltantes detectados.</p>}
                    </div>
                  </Card>

                  <Card className="p-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">En otra ubicación</p>
                      <Badge variant="outline">{scannerAnalysis.wrongLocation.length}</Badge>
                    </div>
                    <div className="text-xs text-muted-foreground space-y-1 max-h-40 overflow-auto">
                      {scannerAnalysis.wrongLocation.slice(0, 12).map(item => (
                        <p key={item.imei}>{item.imei} · {item.product_name || 'Sin producto'} · {item.location_name || item.detail}</p>
                      ))}
                      {!scannerAnalysis.wrongLocation.length && <p>No hay IMEIs de otras ubicaciones.</p>}
                    </div>
                  </Card>

                  <Card className="p-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">Bloqueados</p>
                      <Badge variant="outline">{scannerAnalysis.blocked.length}</Badge>
                    </div>
                    <div className="text-xs text-muted-foreground space-y-1 max-h-40 overflow-auto">
                      {scannerAnalysis.blocked.slice(0, 12).map(item => (
                        <p key={item.imei}>{item.imei} · {item.product_name || 'Sin producto'} · {item.detail}</p>
                      ))}
                      {!scannerAnalysis.blocked.length && <p>No hay IMEIs reservados, vendidos o en traslado.</p>}
                    </div>
                  </Card>

                  <Card className="p-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">Duplicados e inválidos</p>
                      <Badge variant="outline">{scannerAnalysis.duplicateImeis.length + scannerAnalysis.unknown.length}</Badge>
                    </div>
                    <div className="text-xs text-muted-foreground space-y-1 max-h-40 overflow-auto">
                      {scannerAnalysis.duplicateImeis.slice(0, 8).map(imei => (
                        <p key={`dup-${imei}`}>{imei} · escaneado más de una vez</p>
                      ))}
                      {scannerAnalysis.unknown.slice(0, 8).map(item => (
                        <p key={`unknown-${item.imei}`}>{item.imei} · {item.detail || 'no existe en el sistema'}</p>
                      ))}
                      {!scannerAnalysis.duplicateImeis.length && !scannerAnalysis.unknown.length && <p>No hay duplicados ni códigos inválidos.</p>}
                    </div>
                  </Card>
                </div>
              </Card>

              <Card className="p-3">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <h3 className="font-medium">Productos contados</h3>
                  <Button size="sm" variant="outline" onClick={() => setCountLines(current => [...current, createCountLine(firstProductId)])}>
                    <Plus size={16} className="mr-2" />Agregar línea
                  </Button>
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Producto</TableHead>
                      <TableHead className="w-36">Cantidad física</TableHead>
                      <TableHead>IMEIs contados</TableHead>
                      <TableHead>Notas</TableHead>
                      <TableHead className="w-12" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {countLines.map(line => {
                      const selectedProduct = activeProducts.find(product => String(product.id) === line.product_id)
                      const imeiCount = parseScannerTokens(line.imeis).filter(isImeiToken).length
                      return (
                      <TableRow key={line.id}>
                        <TableCell className="min-w-56">
                          <div className="space-y-1.5">
                            <Input
                              value={line.product_search}
                              onChange={event => updateCountLine(line.id, { product_search: event.target.value, product_id: '' })}
                              placeholder="Buscar producto, SKU o modelo"
                            />
                            <div className="max-h-28 overflow-y-auto rounded-md border bg-background p-1">
                              {filteredProductsForSearch(line.product_search, line.product_id).length === 0 ? (
                                <p className="px-2 py-1.5 text-xs text-muted-foreground">Sin coincidencias</p>
                              ) : filteredProductsForSearch(line.product_search, line.product_id).map(product => (
                                <button
                                  key={product.id}
                                  type="button"
                                  className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-xs hover:bg-muted"
                                  onClick={() => selectCountProduct(line.id, product)}
                                >
                                  <span className="min-w-0 truncate">{product.nombre}</span>
                                  <Badge variant="secondary" className="shrink-0">{product.sku || 'Sin SKU'}</Badge>
                                </button>
                              ))}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell><Input type="number" min="0" value={line.imeis.trim() ? String(imeiCount) : line.counted_quantity} onChange={event => updateCountLine(line.id, { counted_quantity: event.target.value })} disabled={Boolean(line.imeis.trim())} /></TableCell>
                        <TableCell>
                          <Input
                            value={line.imeis}
                            onChange={event => updateCountLine(line.id, { imeis: event.target.value })}
                            placeholder={selectedProduct?.is_serialized ? 'IMEIs separados por coma' : 'Solo serializados'}
                            disabled={!selectedProduct?.is_serialized}
                          />
                        </TableCell>
                        <TableCell><Input value={line.notes} onChange={event => updateCountLine(line.id, { notes: event.target.value })} placeholder="Opcional" /></TableCell>
                        <TableCell>
                          <Button variant="ghost" size="icon" disabled={countLines.length === 1} onClick={() => setCountLines(current => current.filter(item => item.id !== line.id))}>
                            <Trash size={16} />
                          </Button>
                        </TableCell>
                      </TableRow>
                    )})}
                  </TableBody>
                </Table>
              </Card>

              {permissions.canCountInventory && (
                <>
                  <Textarea value={countNotes} onChange={event => setCountNotes(event.target.value)} placeholder="Notas generales del conteo" rows={2} />
                  <Button onClick={handleCreateCount} disabled={submitting}>Crear conteo</Button>
                </>
              )}

              <div className="space-y-2">
                {counts.map(count => (
                  <Card key={count.id} className="p-3 flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">Conteo #{count.id} · {locationName(count.location_id)}</p>
                      <p className="text-sm text-muted-foreground">{count.items.map(item => `${productName(item.product_id)}: ${item.expected_quantity} → ${item.counted_quantity} (${item.difference >= 0 ? '+' : ''}${item.difference})`).join(', ')}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={count.status === 'approved' ? 'default' : 'outline'}>{count.status}</Badge>
                      {count.status === 'draft' && permissions.canAdjustInventory && <Button size="sm" onClick={() => handleApproveCount(count.id)} disabled={submitting}>Aprobar</Button>}
                    </div>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="closes" className="space-y-4 mt-0">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground">Cierres con diferencia</p>
                  <p className="text-2xl font-semibold">{closeSummary.withDifference}</p>
                </Card>
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground">Diferencia neta</p>
                  <p className="text-2xl font-semibold">{closeSummary.totalDifference.toLocaleString('es-HN', { minimumFractionDigits: 2 })}</p>
                </Card>
                <div className="space-y-1.5">
                  <Label>Ubicación</Label>
                  <Select value={closeLocationId} onValueChange={setCloseLocationId}>
                    <SelectTrigger><SelectValue placeholder="Ubicación" /></SelectTrigger>
                    <SelectContent>{activeLocations.map(location => <SelectItem key={location.id} value={String(location.id)}>{location.nombre}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5"><Label>Fecha</Label><Input type="date" value={closeDate} onChange={event => setCloseDate(event.target.value)} /></div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div className="space-y-1.5"><Label>Efectivo contado</Label><Input type="number" min="0" step="0.01" value={cashCounted} onChange={event => setCashCounted(event.target.value)} /></div>
                <div className="space-y-1.5"><Label>Transferencias</Label><Input type="number" min="0" step="0.01" value={transferTotal} onChange={event => setTransferTotal(event.target.value)} /></div>
                <div className="space-y-1.5"><Label>Tarjeta</Label><Input type="number" min="0" step="0.01" value={cardTotal} onChange={event => setCardTotal(event.target.value)} /></div>
                <div className="space-y-1.5"><Label>Financiamiento</Label><Input type="number" min="0" step="0.01" value={financingTotal} onChange={event => setFinancingTotal(event.target.value)} /></div>
              </div>
              <Textarea value={closeNotes} onChange={event => setCloseNotes(event.target.value)} placeholder="Notas del cierre" rows={2} />
              <Button onClick={handleCreateClose} disabled={submitting}>Registrar cierre</Button>

              <div className="space-y-2">
                {closes.map(close => (
                  <Card key={close.id} className="p-3 flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">Cierre #{close.id} · {locationName(close.location_id)}</p>
                      <p className="text-sm text-muted-foreground">
                        Esperado total {(
                          Number(close.cash_expected || 0) +
                          Number(close.transfer_expected || 0) +
                          Number(close.card_expected || 0) +
                          Number(close.financing_expected || 0)
                        ).toLocaleString('es-HN')} · Contado total {(
                          Number(close.cash_counted || 0) +
                          Number(close.transfer_total || 0) +
                          Number(close.card_total || 0) +
                          Number(close.financing_total || 0)
                        ).toLocaleString('es-HN')} · Diferencia {Number(close.difference).toLocaleString('es-HN')}
                      </p>
                      <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-muted-foreground">
                        {Object.entries(paymentDifference(close)).map(([method, difference]) => (
                          <span key={method} className={difference === 0 ? '' : 'text-destructive font-medium'}>
                            {method}: {difference >= 0 ? '+' : ''}{difference.toLocaleString('es-HN')}
                          </span>
                        ))}
                      </div>
                    </div>
                    <Badge variant={Number(close.difference) === 0 ? 'default' : 'destructive'}>{close.status}</Badge>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="bank" className="space-y-4 mt-0">
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                <div className="space-y-1.5">
                  <Label>Ubicación</Label>
                  <Select value={bankLocationId} onValueChange={setBankLocationId}>
                    <SelectTrigger><SelectValue placeholder="Todas" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todas</SelectItem>
                      {activeLocations.map(location => <SelectItem key={location.id} value={String(location.id)}>{location.nombre}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5"><Label>Desde</Label><Input type="date" value={bankStartDate} onChange={event => setBankStartDate(event.target.value)} /></div>
                <div className="space-y-1.5"><Label>Hasta</Label><Input type="date" value={bankEndDate} onChange={event => setBankEndDate(event.target.value)} /></div>
                <div className="space-y-1.5"><Label>Banco</Label><Input value={bankNameFilter} onChange={event => setBankNameFilter(event.target.value)} placeholder="BAC, Ficohsa..." /></div>
                <div className="flex items-end gap-2">
                  <Button type="button" onClick={loadBankReconciliation} disabled={loading}>Consultar</Button>
                  <Button type="button" variant="outline" onClick={exportBankReconciliationCsv} disabled={!bankReport?.items.length}>CSV</Button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground">Transferencias conciliables</p>
                  <p className="text-2xl font-semibold">{bankReport?.total_orders || 0}</p>
                </Card>
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground">Total transferencias</p>
                  <p className="text-2xl font-semibold">{Number(bankReport?.total_amount || 0).toLocaleString('es-HN', { minimumFractionDigits: 2 })}</p>
                </Card>
              </div>

              <Card className="p-3">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Orden</TableHead>
                      <TableHead>Fecha</TableHead>
                      <TableHead>Cliente</TableHead>
                      <TableHead>Ubicación</TableHead>
                      <TableHead>Banco</TableHead>
                      <TableHead>Referencia</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!bankReport?.items.length ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">No hay transferencias para conciliar.</TableCell>
                      </TableRow>
                    ) : bankReport.items.map(item => (
                      <TableRow key={item.order_id}>
                        <TableCell>#{item.order_id}</TableCell>
                        <TableCell className="whitespace-nowrap">{new Date(item.created_at).toLocaleDateString('es-HN')}</TableCell>
                        <TableCell>{item.customer_name}</TableCell>
                        <TableCell>{item.location_nombre || locationName(item.location_id)}</TableCell>
                        <TableCell>{item.bank_name || '-'}</TableCell>
                        <TableCell>{item.reference || '-'}</TableCell>
                        <TableCell className="text-right">{Number(item.total || 0).toLocaleString('es-HN', { minimumFractionDigits: 2 })}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            </TabsContent>

            <TabsContent value="access" className="space-y-4 mt-0">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Usuario</Label>
                  <Select value={accessUserId} onValueChange={setAccessUserId}>
                    <SelectTrigger><SelectValue placeholder={users.length ? 'Seleccione usuario' : 'Sin permiso para listar usuarios'} /></SelectTrigger>
                    <SelectContent>
                      {users.map(user => <SelectItem key={user.id} value={String(user.id)}>{userName(user)}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Ubicación</Label>
                  <Select value={accessLocationId} onValueChange={setAccessLocationId}>
                    <SelectTrigger><SelectValue placeholder="Ubicación" /></SelectTrigger>
                    <SelectContent>{activeLocations.map(location => <SelectItem key={location.id} value={String(location.id)}>{location.nombre}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {Object.entries(accessFlags).map(([key, value]) => (
                  <label key={key} className="flex items-center gap-2 rounded-md border p-2 text-sm">
                    <Checkbox checked={value} onCheckedChange={checked => setAccessFlags(current => ({ ...current, [key]: Boolean(checked) }))} />
                    {accessLabels[key as keyof typeof accessLabels]}
                  </label>
                ))}
              </div>
              <Button onClick={handleSaveAccess} disabled={submitting || !users.length}>
                <UserIcon size={16} className="mr-2" />Guardar acceso
              </Button>
            </TabsContent>

            <TabsContent value="audit" className="space-y-2 mt-0">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div className="space-y-1.5">
                  <Label>Ubicación</Label>
                  <Select value={auditLocationId} onValueChange={setAuditLocationId}>
                    <SelectTrigger><SelectValue placeholder="Todas" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todas</SelectItem>
                      {activeLocations.map(location => <SelectItem key={location.id} value={String(location.id)}>{location.nombre}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5"><Label>Entidad</Label><Input value={auditEntityType} onChange={event => setAuditEntityType(event.target.value)} placeholder="order, stock..." /></div>
                <div className="space-y-1.5"><Label>Acción</Label><Input value={auditAction} onChange={event => setAuditAction(event.target.value)} placeholder="order.created" /></div>
                <div className="flex items-end">
                  <Button type="button" variant="outline" onClick={handleApplyAuditFilters} disabled={loading}>Filtrar</Button>
                </div>
              </div>
              {auditLogs.map(log => (
                <Card key={log.id} className="p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{log.action} · {log.entity_type}{log.entity_id ? ` #${log.entity_id}` : ''}</p>
                      <p className="text-xs text-muted-foreground">{log.username || 'sistema'} · {log.location_id ? locationName(log.location_id) : 'Sin ubicación'} · {new Date(log.created_at).toLocaleString('es-HN')}</p>
                    </div>
                    <Badge variant="outline">Auditoría</Badge>
                  </div>
                </Card>
              ))}
              {!auditLogs.length && !loading && <p className="text-sm text-muted-foreground py-6 text-center">No hay eventos de auditoría recientes.</p>}
            </TabsContent>
          </ScrollArea>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
