import { useEffect, useMemo, useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'
import { ArrowsLeftRight, Barcode, ClockCounterClockwise, CreditCard, Package, Plus, ShieldCheck, ShoppingCart, Trash, WarningCircle } from '@phosphor-icons/react'

import { apiClient } from '@/lib/apiClient'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { ProductIMEIRegistryDialog } from './ProductIMEIRegistryDialog'
import type {
  Location,
  OrderWithItems,
  PaymentBreakdownEntry,
  ProductWithStock,
  StockTransfer,
  SuperAdminAlert,
  SuperAdminAuditLogEntry,
  SuperAdminEntityHistory,
  SuperAdminStockImeiIssue,
  SuperAdminUserSummary,
} from '@/lib/types'

interface SuperAdminControlPanelDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  products: ProductWithStock[]
  locations: Location[]
  orders: OrderWithItems[]
  onUpdated?: () => Promise<void> | void
}

type PaymentMethod = PaymentBreakdownEntry['method']

interface PaymentCorrectionLine {
  id: string
  method: PaymentMethod
  amount: string
  bank_name: string
  reference: string
}

interface PendingConfirmation {
  title: string
  description: string
  confirmLabel: string
  dangerous?: boolean
  requiredText?: string
  run: () => Promise<void>
}

const emptyEntityHistory: SuperAdminEntityHistory = {
  audit_logs: [],
  stock_history: [],
  imei_history: [],
}

const paymentMethods: PaymentMethod[] = ['efectivo', 'transferencia', 'tarjeta', 'financiamiento']
const paymentMethodLabels: Record<PaymentMethod, string> = {
  efectivo: 'Efectivo',
  transferencia: 'Transferencia',
  tarjeta: 'Tarjeta',
  financiamiento: 'Financiamiento',
}

const createPaymentLine = (entry?: PaymentBreakdownEntry): PaymentCorrectionLine => ({
  id: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
  method: entry?.method || 'efectivo',
  amount: entry ? String(entry.amount) : '',
  bank_name: entry?.bank_name || '',
  reference: entry?.reference || '',
})

export function SuperAdminControlPanelDialog({
  open,
  onOpenChange,
  products,
  locations,
  orders,
  onUpdated,
}: SuperAdminControlPanelDialogProps) {
  const [issues, setIssues] = useState<SuperAdminStockImeiIssue[]>([])
  const [transfers, setTransfers] = useState<StockTransfer[]>([])
  const [loadingDiagnostics, setLoadingDiagnostics] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [activeTab, setActiveTab] = useState('diagnostics')
  const [confirmText, setConfirmText] = useState('')

  const [stockProductSearch, setStockProductSearch] = useState('')
  const [stockProductId, setStockProductId] = useState('')
  const [stockLocationId, setStockLocationId] = useState('')
  const [stockAvailable, setStockAvailable] = useState('0')
  const [stockReserved, setStockReserved] = useState('0')
  const [stockDefective, setStockDefective] = useState('0')
  const [stockReason, setStockReason] = useState('')

  const [orderId, setOrderId] = useState('')
  const [orderSearch, setOrderSearch] = useState('')
  const [orderReason, setOrderReason] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('')
  const [paymentLines, setPaymentLines] = useState<PaymentCorrectionLine[]>([])
  const [transferBankName, setTransferBankName] = useState('')
  const [transferReference, setTransferReference] = useState('')
  const [paymentNotes, setPaymentNotes] = useState('')

  const [transferId, setTransferId] = useState('')
  const [transferSearch, setTransferSearch] = useState('')
  const [transferReason, setTransferReason] = useState('')

  const [catalogProductSearch, setCatalogProductSearch] = useState('')
  const [catalogProductId, setCatalogProductId] = useState('')
  const [catalogSku, setCatalogSku] = useState('')
  const [catalogName, setCatalogName] = useState('')
  const [catalogBrand, setCatalogBrand] = useState('')
  const [catalogModel, setCatalogModel] = useState('')
  const [catalogColor, setCatalogColor] = useState('')
  const [catalogCapacity, setCatalogCapacity] = useState('')
  const [catalogPrice, setCatalogPrice] = useState('0')
  const [catalogCost, setCatalogCost] = useState('0')
  const [catalogActive, setCatalogActive] = useState(true)
  const [catalogReason, setCatalogReason] = useState('')
  const [pendingConfirmation, setPendingConfirmation] = useState<PendingConfirmation | null>(null)

  const [imeiProductSearch, setImeiProductSearch] = useState('')
  const [imeiRegistryProduct, setImeiRegistryProduct] = useState<ProductWithStock | null>(null)

  const [auditLogs, setAuditLogs] = useState<SuperAdminAuditLogEntry[]>([])
  const [auditUsername, setAuditUsername] = useState('')
  const [auditAction, setAuditAction] = useState('')
  const [auditEntityType, setAuditEntityType] = useState('')
  const [auditEntityId, setAuditEntityId] = useState('')
  const [auditStartDate, setAuditStartDate] = useState('')
  const [auditEndDate, setAuditEndDate] = useState('')
  const [auditReason, setAuditReason] = useState('')

  const [historyFilters, setHistoryFilters] = useState({ entity_type: '', entity_id: '', product_id: '', location_id: '', imei: '' })
  const [entityHistory, setEntityHistory] = useState<SuperAdminEntityHistory>(emptyEntityHistory)

  const [alerts, setAlerts] = useState<SuperAdminAlert[]>([])
  const [staleTransferDays, setStaleTransferDays] = useState('2')

  const [adminUsers, setAdminUsers] = useState<SuperAdminUserSummary[]>([])
  const [userSearch, setUserSearch] = useState('')
  const [selectedUserId, setSelectedUserId] = useState('')
  const [userReason, setUserReason] = useState('')

  const catalogProducts = useMemo(() => products, [products])
  const activeLocations = useMemo(() => locations.filter(location => location.activo !== false), [locations])
  const pendingTransfers = useMemo(() => transfers.filter(transfer => transfer.estado === 'pendiente'), [transfers])
  const selectedStockProduct = catalogProducts.find(product => String(product.id) === stockProductId)
  const selectedStock = selectedStockProduct?.stock_items?.find(stock => String(stock.location_id) === stockLocationId)
  const selectedOrder = orders.find(order => String(order.id) === orderId)
  const selectedTransfer = pendingTransfers.find(transfer => String(transfer.id) === transferId)
  const selectedCatalogProduct = catalogProducts.find(product => String(product.id) === catalogProductId)
  const selectedUser = adminUsers.find(user => String(user.id) === selectedUserId)

  const paymentLinesTotal = paymentLines.reduce((sum, line) => sum + (Number(line.amount) || 0), 0)
  const selectedOrderTotal = Number(selectedOrder?.total || 0)
  const paymentDifference = selectedOrder ? paymentLinesTotal - selectedOrderTotal : 0

  const filteredProducts = useMemo(() => {
    const tokens = stockProductSearch.trim().toLowerCase().split(/\s+/).filter(Boolean)
    return catalogProducts.filter(product => {
      if (tokens.length === 0) return true
      const search = [product.nombre, product.sku, product.marca, product.modelo, product.color, product.capacidad].filter(Boolean).join(' ').toLowerCase()
      return tokens.every(token => search.includes(token))
    }).slice(0, 10)
  }, [catalogProducts, stockProductSearch])

  const filteredCatalogProducts = useMemo(() => {
    const tokens = catalogProductSearch.trim().toLowerCase().split(/\s+/).filter(Boolean)
    return catalogProducts.filter(product => {
      if (tokens.length === 0) return true
      const search = [product.nombre, product.sku, product.marca, product.modelo, product.color, product.capacidad].filter(Boolean).join(' ').toLowerCase()
      return tokens.every(token => search.includes(token))
    }).slice(0, 10)
  }, [catalogProducts, catalogProductSearch])

  const filteredImeiProducts = useMemo(() => {
    const tokens = imeiProductSearch.trim().toLowerCase().split(/\s+/).filter(Boolean)
    return products.filter(product => {
      const isSerialized = Boolean(product.is_serialized || product.categoria === 'celular')
      if (!isSerialized) return false
      if (tokens.length === 0) return true
      const search = [product.nombre, product.sku, product.marca, product.modelo, product.color, product.capacidad].filter(Boolean).join(' ').toLowerCase()
      return tokens.every(token => search.includes(token))
    }).slice(0, 12)
  }, [products, imeiProductSearch])

  const filteredOrders = useMemo(() => {
    const tokens = orderSearch.trim().toLowerCase().split(/\s+/).filter(Boolean)
    return orders.filter(order => {
      if (tokens.length === 0) return true
      const search = [order.id, order.customer_name, order.customer_phone, order.estado, order.total].filter(Boolean).join(' ').toLowerCase()
      return tokens.every(token => search.includes(token))
    }).slice(0, 12)
  }, [orders, orderSearch])

  const filteredTransfers = useMemo(() => {
    const tokens = transferSearch.trim().toLowerCase().split(/\s+/).filter(Boolean)
    return pendingTransfers.filter(transfer => {
      if (tokens.length === 0) return true
      const search = [transfer.id, transfer.product_nombre, transfer.product_sku, transfer.from_location_name, transfer.to_location_name].filter(Boolean).join(' ').toLowerCase()
      return tokens.every(token => search.includes(token))
    }).slice(0, 12)
  }, [pendingTransfers, transferSearch])

  const loadDiagnostics = async () => {
    setLoadingDiagnostics(true)
    try {
      const result = await apiClient.getSuperAdminStockImeiDiagnostics()
      setIssues(result.issues)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo cargar diagnóstico')
    } finally {
      setLoadingDiagnostics(false)
    }
  }

  const loadTransfers = async () => {
    try {
      const data = await inventoryServiceInstance.listStockTransfers({ estado: 'pendiente' })
      setTransfers(data)
    } catch {
      setTransfers([])
    }
  }

  const loadAuditLogs = async (overrides: Partial<{
    username: string
    action: string
    entity_type: string
    entity_id: string
    start_date: string
    end_date: string
  }> = {}) => {
    try {
      const filters = {
        username: overrides.username ?? auditUsername,
        action: overrides.action ?? auditAction,
        entity_type: overrides.entity_type ?? auditEntityType,
        entity_id: overrides.entity_id ?? auditEntityId,
        start_date: overrides.start_date ?? auditStartDate,
        end_date: overrides.end_date ?? auditEndDate,
      }
      const result = await apiClient.getSuperAdminAuditLogs({
        username: filters.username,
        action: filters.action,
        entity_type: filters.entity_type,
        entity_id: filters.entity_id ? Number(filters.entity_id) : undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined,
        super_admin_only: true,
        limit: 150,
      })
      setAuditLogs(result.items)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo cargar auditoría')
    }
  }

  const loadEntityHistory = async (overrideFilters = historyFilters) => {
    try {
      const result = await apiClient.getSuperAdminEntityHistory({
        entity_type: overrideFilters.entity_type || undefined,
        entity_id: overrideFilters.entity_id ? Number(overrideFilters.entity_id) : undefined,
        product_id: overrideFilters.product_id ? Number(overrideFilters.product_id) : undefined,
        location_id: overrideFilters.location_id ? Number(overrideFilters.location_id) : undefined,
        imei: overrideFilters.imei || undefined,
      })
      setEntityHistory(result)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo cargar historial')
    }
  }

  const loadAlerts = async () => {
    try {
      const result = await apiClient.getSuperAdminAlerts(Number(staleTransferDays) || 2)
      setAlerts(result.items)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudieron cargar alertas')
    }
  }

  const loadUsers = async () => {
    try {
      const result = await apiClient.getSuperAdminUsers(userSearch)
      setAdminUsers(result.items)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudieron cargar usuarios')
    }
  }

  const refreshPanelData = async () => {
    await onUpdated?.()
    await Promise.all([
      loadDiagnostics(),
      loadTransfers(),
      loadAuditLogs(),
      loadAlerts(),
      loadUsers(),
    ])
  }

  const exportCsv = (filename: string, rows: Array<Record<string, unknown>>) => {
    if (rows.length === 0) {
      toast.error('No hay datos para exportar')
      return
    }
    const headers = Array.from(rows.reduce((set, row) => {
      Object.keys(row).forEach(key => set.add(key))
      return set
    }, new Set<string>()))
    const escape = (value: unknown) => {
      const text = typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value ?? '')
      return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
    }
    const csv = [headers.join(','), ...rows.map(row => headers.map(header => escape(row[header])).join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  useEffect(() => {
    if (!open) return
    void loadDiagnostics()
    void loadTransfers()
    void loadAuditLogs()
    void loadAlerts()
    void loadUsers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    if (!selectedStock) return
    setStockAvailable(String(selectedStock.cantidad_disponible ?? 0))
    setStockReserved(String(selectedStock.cantidad_reservada ?? 0))
    setStockDefective(String(selectedStock.cantidad_defectuosa ?? 0))
  }, [selectedStock])

  const requireReason = (reason: string) => {
    if (reason.trim().length < 5) {
      toast.error('Escribe un motivo claro de al menos 5 caracteres')
      return false
    }
    return true
  }

  const requestConfirmation = (confirmation: PendingConfirmation) => {
    setConfirmText('')
    setPendingConfirmation(confirmation)
  }

  const runPendingConfirmation = async () => {
    const action = pendingConfirmation
    if (!action) return
    await action.run()
    setPendingConfirmation(null)
  }

  const updatePaymentLine = (lineId: string, updates: Partial<PaymentCorrectionLine>) => {
    setPaymentLines(previous => previous.map(line => line.id === lineId ? { ...line, ...updates } : line))
  }

  const removePaymentLine = (lineId: string) => {
    setPaymentLines(previous => previous.filter(line => line.id !== lineId))
  }

  const buildPaymentBreakdown = (): PaymentBreakdownEntry[] | undefined => {
    if (paymentLines.length === 0) return undefined

    return paymentLines.map(line => ({
      method: line.method,
      amount: Number(line.amount),
      bank_name: line.method === 'transferencia' ? line.bank_name.trim() || undefined : undefined,
      reference: line.method === 'transferencia' ? line.reference.trim() || undefined : undefined,
    }))
  }

  const validatePaymentCorrection = () => {
    const parsedBreakdown = buildPaymentBreakdown()

    if (parsedBreakdown) {
      const invalidAmount = parsedBreakdown.find(line => !Number.isFinite(line.amount) || line.amount <= 0)
      if (invalidAmount) {
        toast.error('Cada fila del desglose debe tener un monto mayor a 0')
        return null
      }

      if (selectedOrder && Math.abs(paymentLinesTotal - selectedOrderTotal) >= 0.01) {
        toast.error('El desglose de pagos debe cuadrar con el total de la orden')
        return null
      }

      const missingTransferData = parsedBreakdown.find(line => line.method === 'transferencia' && (!line.bank_name || !line.reference))
      if (missingTransferData) {
        toast.error('Cada pago por transferencia debe incluir banco y referencia')
        return null
      }
    }

    if ((paymentMethod === 'transferencia' || transferBankName.trim() || transferReference.trim()) && (!transferBankName.trim() || !transferReference.trim())) {
      toast.error('Para transferencia debes indicar banco y referencia')
      return null
    }

    return parsedBreakdown
  }

  const validateStockNumbers = () => {
    const available = Number(stockAvailable)
    const reserved = Number(stockReserved)
    const defective = Number(stockDefective)
    if (![available, reserved, defective].every(value => Number.isFinite(value) && Number.isInteger(value))) {
      toast.error('Los valores de stock deben ser números enteros válidos')
      return false
    }
    if (available < 0 || reserved < 0 || defective < 0) {
      toast.error('Los valores de stock no pueden ser negativos')
      return false
    }
    if (reserved > available) {
      toast.error('El stock reservado no puede ser mayor que el disponible')
      return false
    }
    return true
  }

  const handleAdjustStock = async () => {
    if (!stockProductId || !stockLocationId) {
      toast.error('Selecciona producto y ubicación')
      return
    }
    if (!validateStockNumbers()) return
    if (!requireReason(stockReason)) return

    setSubmitting(true)
    try {
      await apiClient.superAdminAdjustStock({
        product_id: Number(stockProductId),
        location_id: Number(stockLocationId),
        cantidad_disponible: Number(stockAvailable) || 0,
        cantidad_reservada: Number(stockReserved) || 0,
        cantidad_defectuosa: Number(stockDefective) || 0,
        reason: stockReason,
      })
      toast.success('Stock ajustado con auditoría')
      setStockReason('')
      await refreshPanelData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al ajustar stock')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancelOrder = async () => {
    if (!orderId) {
      toast.error('Selecciona una orden')
      return
    }
    if (!requireReason(orderReason)) return

    setSubmitting(true)
    try {
      await apiClient.superAdminCancelOrder(Number(orderId), orderReason)
      toast.success('Orden cancelada por Super Admin')
      setOrderReason('')
      await refreshPanelData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al cancelar orden')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCorrectPayment = async () => {
    if (!orderId) {
      toast.error('Selecciona una orden')
      return
    }
    if (!requireReason(orderReason)) return

    const parsedBreakdown = validatePaymentCorrection()
    if (parsedBreakdown === null) return

    setSubmitting(true)
    try {
      await apiClient.superAdminCorrectOrderPayment(Number(orderId), {
        metodo_pago: paymentMethod || undefined,
        payment_breakdown: parsedBreakdown,
        transfer_bank_name: transferBankName.trim(),
        transfer_reference: transferReference.trim(),
        notes: paymentNotes || undefined,
        reason: orderReason,
      })
      toast.success('Pago corregido con auditoría')
      setPaymentNotes('')
      await refreshPanelData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al corregir pago')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancelTransfer = async () => {
    if (!transferId) {
      toast.error('Selecciona una transferencia')
      return
    }
    if (!requireReason(transferReason)) return

    setSubmitting(true)
    try {
      await apiClient.superAdminCancelTransfer(Number(transferId), transferReason)
      toast.success('Transferencia cancelada por Super Admin')
      setTransferReason('')
      await refreshPanelData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al cancelar transferencia')
    } finally {
      setSubmitting(false)
    }
  }

  const selectOrder = (order: OrderWithItems) => {
    setOrderId(String(order.id))
    setOrderSearch(`#${order.id} · ${order.customer_name} · ${order.estado}`)
    setPaymentMethod(order.metodo_pago || '')
    setTransferBankName(order.transfer_bank_name || '')
    setTransferReference(order.transfer_reference || '')
    setPaymentLines(order.payment_breakdown?.length ? order.payment_breakdown.map(createPaymentLine) : [])
  }

  const selectTransfer = (transfer: StockTransfer) => {
    setTransferId(String(transfer.id))
    setTransferSearch(`#${transfer.id} · ${transfer.product_nombre || 'Producto'} · ${transfer.from_location_name || 'Origen'} a ${transfer.to_location_name || 'Destino'}`)
  }

  const selectCatalogProduct = (product: ProductWithStock) => {
    setCatalogProductId(String(product.id))
    setCatalogProductSearch(product.nombre)
    setCatalogSku(product.sku || '')
    setCatalogName(product.nombre || '')
    setCatalogBrand(product.marca || '')
    setCatalogModel(product.modelo || '')
    setCatalogColor(product.color || '')
    setCatalogCapacity(product.capacidad || '')
    setCatalogPrice(String(product.precio ?? 0))
    setCatalogCost(String(product.costo ?? 0))
    setCatalogActive(product.activo !== false)
  }

  const openImeiRegistry = (product: ProductWithStock) => {
    setImeiRegistryProduct(product)
    setImeiProductSearch(product.nombre)
  }

  const handleCorrectProduct = async () => {
    if (!catalogProductId) {
      toast.error('Selecciona un producto')
      return
    }
    if (!requireReason(catalogReason)) return
    if (!catalogSku.trim() || !catalogName.trim()) {
      toast.error('SKU y nombre no pueden quedar vacíos')
      return
    }

    setSubmitting(true)
    try {
      await apiClient.superAdminCorrectProduct(Number(catalogProductId), {
        sku: catalogSku.trim(),
        nombre: catalogName.trim(),
        marca: catalogBrand.trim() || undefined,
        modelo: catalogModel.trim() || undefined,
        color: catalogColor.trim(),
        capacidad: catalogCapacity.trim(),
        precio: Number(catalogPrice) || 0,
        costo: Number(catalogCost) || 0,
        activo: catalogActive,
        reason: catalogReason,
      })
      toast.success('Producto corregido con auditoría')
      setCatalogReason('')
      await refreshPanelData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al corregir producto')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSetUserActive = async (isActive: boolean) => {
    if (!selectedUserId) {
      toast.error('Selecciona un usuario')
      return
    }
    if (!requireReason(userReason)) return
    setSubmitting(true)
    try {
      await apiClient.superAdminSetUserActive(Number(selectedUserId), { is_active: isActive, reason: userReason })
      toast.success(isActive ? 'Usuario activado' : 'Usuario bloqueado')
      setUserReason('')
      await refreshPanelData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al actualizar usuario')
    } finally {
      setSubmitting(false)
    }
  }

  const handleResetUserRole = async () => {
    if (!selectedUserId) {
      toast.error('Selecciona un usuario')
      return
    }
    if (!requireReason(userReason)) return
    setSubmitting(true)
    try {
      await apiClient.superAdminResetUserRole(Number(selectedUserId), userReason)
      toast.success('Rol reseteado')
      setUserReason('')
      await refreshPanelData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al resetear rol')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRevertAudit = async (auditId: number) => {
    if (!requireReason(auditReason)) return
    setSubmitting(true)
    try {
      await apiClient.superAdminRevertAudit(auditId, auditReason)
      toast.success('Corrección revertida con nueva auditoría')
      setAuditReason('')
      await refreshPanelData()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo revertir')
    } finally {
      setSubmitting(false)
    }
  }

  const confirmAdjustStock = () => {
    if (!stockProductId || !stockLocationId || !validateStockNumbers() || !requireReason(stockReason)) return
    requestConfirmation({
      title: 'Confirmar ajuste de stock',
      description: `${selectedStockProduct?.nombre || 'Producto'} en ${activeLocations.find(location => String(location.id) === stockLocationId)?.nombre || 'ubicación seleccionada'} quedará con ${stockAvailable} disponible(s), ${stockReserved} reservado(s) y ${stockDefective} defectuoso(s).`,
      confirmLabel: 'Aplicar ajuste',
      run: handleAdjustStock,
    })
  }

  const confirmCorrectPayment = () => {
    if (!orderId || !requireReason(orderReason)) return
    const parsedBreakdown = validatePaymentCorrection()
    if (parsedBreakdown === null) return
    requestConfirmation({
      title: 'Confirmar corrección de pago',
      description: `Se actualizarán los datos de pago de la orden #${orderId}. Esta acción quedará auditada con el motivo indicado.`,
      confirmLabel: 'Corregir pago',
      run: handleCorrectPayment,
    })
  }

  const confirmCancelOrder = () => {
    if (!orderId || !requireReason(orderReason)) return
    requestConfirmation({
      title: 'Cancelar orden y devolver stock',
      description: `La orden #${orderId} será cancelada y el backend intentará devolver stock e IMEIs según el estado actual de la orden.`,
      confirmLabel: 'Cancelar orden',
      dangerous: true,
      requiredText: 'CONFIRMAR',
      run: handleCancelOrder,
    })
  }

  const confirmCancelTransfer = () => {
    if (!transferId || !requireReason(transferReason)) return
    requestConfirmation({
      title: 'Cancelar transferencia pendiente',
      description: `La transferencia #${transferId} se marcará como cancelada y se liberará el stock reservado.`,
      confirmLabel: 'Cancelar transferencia',
      dangerous: true,
      requiredText: 'CONFIRMAR',
      run: handleCancelTransfer,
    })
  }

  const confirmCorrectProduct = () => {
    if (!catalogProductId || !requireReason(catalogReason)) return
    requestConfirmation({
      title: 'Guardar corrección de producto',
      description: `${selectedCatalogProduct?.nombre || 'Producto seleccionado'} será actualizado en catálogo con auditoría de antes/después.`,
      confirmLabel: 'Guardar corrección',
      run: handleCorrectProduct,
    })
  }

  const confirmSetUserActive = (isActive: boolean) => {
    if (!selectedUserId || !requireReason(userReason)) return
    requestConfirmation({
      title: isActive ? 'Activar usuario' : 'Bloquear usuario',
      description: `${selectedUser?.username || 'Usuario seleccionado'} quedará ${isActive ? 'activo' : 'bloqueado'} para acceso al sistema.`,
      confirmLabel: isActive ? 'Activar' : 'Bloquear',
      dangerous: !isActive,
      requiredText: !isActive ? 'CONFIRMAR' : undefined,
      run: () => handleSetUserActive(isActive),
    })
  }

  const confirmResetUserRole = () => {
    if (!selectedUserId || !requireReason(userReason)) return
    requestConfirmation({
      title: 'Resetear rol de usuario',
      description: `${selectedUser?.username || 'Usuario seleccionado'} pasará a rol Invitado si existe, o quedará sin rol.`,
      confirmLabel: 'Resetear rol',
      dangerous: true,
      requiredText: 'CONFIRMAR',
      run: handleResetUserRole,
    })
  }

  const confirmRevertAudit = (audit: SuperAdminAuditLogEntry) => {
    if (!requireReason(auditReason)) return
    requestConfirmation({
      title: 'Revertir corrección auditada',
      description: `Se intentará revertir la acción ${audit.action} #${audit.id} usando sus datos previos. Se creará una nueva auditoría de reversa.`,
      confirmLabel: 'Revertir',
      dangerous: true,
      requiredText: 'CONFIRMAR',
      run: () => handleRevertAudit(audit.id),
    })
  }

  const selectProduct = (product: ProductWithStock) => {
    setStockProductId(String(product.id))
    setStockProductSearch(product.nombre)
    const firstStock = product.stock_items?.[0]
    if (firstStock) setStockLocationId(String(firstStock.location_id))
  }

  const prepareStockAdjustmentFromIssue = (issue: SuperAdminStockImeiIssue) => {
    const product = catalogProducts.find(item => item.id === issue.product_id)
    const stock = product?.stock_items?.find(item => item.location_id === issue.location_id)
    const reserved = Number(stock?.cantidad_reservada || 0)
    const defective = Number(stock?.cantidad_defectuosa || 0)

    setStockProductId(String(issue.product_id))
    setStockProductSearch(issue.product_name)
    setStockLocationId(String(issue.location_id))
    setStockAvailable(String(issue.imeis_disponibles + reserved))
    setStockReserved(String(reserved))
    setStockDefective(String(defective))
    setStockReason(`Corrección por diagnóstico stock/IMEI: stock libre ${issue.stock_disponible}, IMEIs disponibles ${issue.imeis_disponibles}`)
    setActiveTab('stock')
  }

  const prepareDefectiveAdjustmentFromIssue = (issue: SuperAdminStockImeiIssue) => {
    const product = catalogProducts.find(item => item.id === issue.product_id)
    const stock = product?.stock_items?.find(item => item.location_id === issue.location_id)
    const reserved = Number(stock?.cantidad_reservada || 0)
    const defective = Number(stock?.cantidad_defectuosa || 0)
    const extraUnits = Math.max(issue.difference, 0)

    setStockProductId(String(issue.product_id))
    setStockProductSearch(issue.product_name)
    setStockLocationId(String(issue.location_id))
    setStockAvailable(String(issue.imeis_disponibles + reserved))
    setStockReserved(String(reserved))
    setStockDefective(String(defective + extraUnits))
    setStockReason(`Diferencia marcada como defectuosa por diagnóstico stock/IMEI: ${extraUnits} unidad(es)`)
    setActiveTab('stock')
  }

  const investigateIssue = (issue: SuperAdminStockImeiIssue) => {
    const nextFilters = { entity_type: 'product', entity_id: String(issue.product_id), product_id: String(issue.product_id), location_id: String(issue.location_id), imei: '' }
    setHistoryFilters(nextFilters)
    setActiveTab('history')
    void loadEntityHistory(nextFilters)
  }

  const openImeiRegistryFromIssue = (issue: SuperAdminStockImeiIssue) => {
    const product = products.find(item => item.id === issue.product_id)
    if (!product) {
      toast.error('No se encontró el producto del diagnóstico')
      return
    }
    openImeiRegistry(product)
  }

  const investigateAlert = (alert: SuperAdminAlert) => {
    if (alert.category === 'stock' && alert.entity_id) {
      const product = products.find(item => item.stock_items?.some(stock => stock.id === alert.entity_id))
      const stock = product?.stock_items?.find(item => item.id === alert.entity_id)
      if (product && stock) {
        setStockProductId(String(product.id))
        setStockProductSearch(product.nombre)
        setStockLocationId(String(stock.location_id))
        setStockAvailable(String(stock.cantidad_disponible ?? 0))
        setStockReserved(String(stock.cantidad_reservada ?? 0))
        setStockDefective(String(stock.cantidad_defectuosa ?? 0))
        setStockReason(`Corrección por alerta de stock inconsistente: ${alert.detail}`)
        setActiveTab('stock')
        return
      }
    }

    if (alert.category === 'imei_stock' && alert.entity_id) {
      const issue = issues.find(item => item.product_id === alert.entity_id && item.location_id === alert.location_id)
      if (issue) {
        prepareStockAdjustmentFromIssue(issue)
        return
      }
    }

    if (alert.category === 'transfer' && alert.entity_id) {
      const transfer = transfers.find(item => item.id === alert.entity_id)
      if (transfer) {
        selectTransfer(transfer)
        setTransferReason(`Corrección por alerta: ${alert.detail}`)
        setActiveTab('transfers')
        return
      }
    }

    if (alert.category === 'security') {
      setAuditAction('super_admin.access.denied')
      setActiveTab('audit')
      void loadAuditLogs({ action: 'super_admin.access.denied' })
      return
    }

    const nextFilters = {
      entity_type: alert.entity_type || '',
      entity_id: alert.entity_id ? String(alert.entity_id) : '',
      product_id: alert.entity_type === 'product' && alert.entity_id ? String(alert.entity_id) : '',
      location_id: alert.location_id ? String(alert.location_id) : '',
      imei: '',
    }
    setHistoryFilters(nextFilters)
    setActiveTab('history')
    void loadEntityHistory(nextFilters)
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck size={22} weight="fill" className="text-red-600" />
            Panel de Control Super Admin
          </DialogTitle>
          <DialogDescription>
            Correcciones críticas con motivo obligatorio, backend protegido y auditoría de antes/después.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="flex flex-wrap h-auto gap-1 w-full justify-start">
            <TabsTrigger value="diagnostics"><WarningCircle size={16} className="mr-1" />Diagnóstico</TabsTrigger>
            <TabsTrigger value="stock"><Package size={16} className="mr-1" />Stock</TabsTrigger>
            <TabsTrigger value="imeis"><Barcode size={16} className="mr-1" />IMEIs</TabsTrigger>
            <TabsTrigger value="orders"><ShoppingCart size={16} className="mr-1" />Órdenes/Pagos</TabsTrigger>
            <TabsTrigger value="transfers"><ArrowsLeftRight size={16} className="mr-1" />Transferencias</TabsTrigger>
            <TabsTrigger value="products"><Package size={16} className="mr-1" />Productos</TabsTrigger>
            <TabsTrigger value="audit"><ClockCounterClockwise size={16} className="mr-1" />Auditoría</TabsTrigger>
            <TabsTrigger value="history"><ClockCounterClockwise size={16} className="mr-1" />Historial</TabsTrigger>
            <TabsTrigger value="alerts"><WarningCircle size={16} className="mr-1" />Alertas</TabsTrigger>
            <TabsTrigger value="users"><ShieldCheck size={16} className="mr-1" />Usuarios</TabsTrigger>
            <TabsTrigger value="reports"><Package size={16} className="mr-1" />Reportes</TabsTrigger>
          </TabsList>

          <TabsContent value="diagnostics" className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="font-semibold">Diferencias entre stock e IMEIs</h3>
                <p className="text-sm text-muted-foreground">Detecta celulares donde el stock libre no coincide con IMEIs disponibles.</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={loadDiagnostics} disabled={loadingDiagnostics}>Actualizar</Button>
                <Button variant="outline" onClick={() => exportCsv('diagnostico_stock_imeis.csv', issues as unknown as Array<Record<string, unknown>>)}>CSV</Button>
              </div>
            </div>
            {issues.length === 0 ? (
              <Card className="p-4 text-sm text-muted-foreground">No hay diferencias detectadas.</Card>
            ) : issues.map(issue => (
              <Card key={`${issue.product_id}-${issue.location_id}`} className="p-3 flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{issue.product_name}</p>
                  <p className="text-sm text-muted-foreground">{issue.location_name || `Ubicación #${issue.location_id}`} · Stock: {issue.stock_disponible} · IMEIs: {issue.imeis_disponibles}</p>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-2">
                  <Badge variant={issue.severity === 'alta' ? 'destructive' : 'secondary'}>Diferencia {issue.difference}</Badge>
                  <Button type="button" variant="outline" size="sm" onClick={() => prepareStockAdjustmentFromIssue(issue)}>
                    Ajustar a IMEIs
                  </Button>
                  <Button type="button" variant="outline" size="sm" onClick={() => openImeiRegistryFromIssue(issue)}>
                    Modificar IMEIs
                  </Button>
                  {issue.difference > 0 && (
                    <Button type="button" variant="outline" size="sm" onClick={() => prepareDefectiveAdjustmentFromIssue(issue)}>
                      Marcar defectuosa
                    </Button>
                  )}
                  <Button type="button" variant="ghost" size="sm" onClick={() => investigateIssue(issue)}>
                    Investigar
                  </Button>
                </div>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="imeis" className="space-y-4">
            <div className="space-y-2">
              <div>
                <h3 className="font-semibold">Corrección administrativa de IMEIs</h3>
                <p className="text-sm text-muted-foreground">Busca un celular, abre su registro y corrige IMEIs disponibles con motivo obligatorio.</p>
              </div>
              <Input value={imeiProductSearch} onChange={event => setImeiProductSearch(event.target.value)} placeholder="Buscar celular por nombre, SKU, marca o modelo" />
              <div className="max-h-64 overflow-y-auto rounded-md border p-1">
                {filteredImeiProducts.length === 0 ? (
                  <p className="px-2 py-2 text-sm text-muted-foreground">No se encontraron productos serializados.</p>
                ) : filteredImeiProducts.map(product => {
                  const availableImeis = product.stock_items?.reduce((total, stock) => total + Number(stock.cantidad_disponible || 0), 0) ?? 0
                  return (
                    <button key={product.id} type="button" className="flex w-full items-center justify-between gap-3 rounded px-2 py-2 text-left text-sm hover:bg-muted" onClick={() => openImeiRegistry(product)}>
                      <span className="min-w-0">
                        <span className="block truncate font-medium">{product.nombre}</span>
                        <span className="block truncate text-xs text-muted-foreground">SKU: {product.sku || 'Sin SKU'} · {product.marca || 'Sin marca'} {product.modelo || ''}</span>
                      </span>
                      <Badge variant="secondary" className="shrink-0">Stock {availableImeis}</Badge>
                    </button>
                  )
                })}
              </div>
            </div>

            <Card className="p-4 text-sm text-muted-foreground">Selecciona un producto de la lista para abrir el editor de IMEIs.</Card>
          </TabsContent>

          <TabsContent value="stock" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Producto</Label>
                <Input value={stockProductSearch} onChange={event => { setStockProductSearch(event.target.value); setStockProductId('') }} placeholder="Buscar producto, SKU o modelo" />
                <div className="max-h-40 overflow-y-auto rounded-md border p-1">
                  {filteredProducts.map(product => (
                    <button key={product.id} type="button" className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-muted" onClick={() => selectProduct(product)}>
                      <span className="truncate">{product.nombre}</span>
                      <Badge variant="secondary">{product.sku || 'Sin SKU'}</Badge>
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label>Ubicación</Label>
                <Select value={stockLocationId} onValueChange={setStockLocationId}>
                  <SelectTrigger><SelectValue placeholder="Seleccionar ubicación" /></SelectTrigger>
                  <SelectContent>
                    {activeLocations.map(location => <SelectItem key={location.id} value={String(location.id)}>{location.nombre}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-2"><Label>Disponible</Label><Input type="number" min="0" value={stockAvailable} onChange={event => setStockAvailable(event.target.value)} /></div>
              <div className="space-y-2"><Label>Reservado</Label><Input type="number" min="0" value={stockReserved} onChange={event => setStockReserved(event.target.value)} /></div>
              <div className="space-y-2"><Label>Defectuoso</Label><Input type="number" min="0" value={stockDefective} onChange={event => setStockDefective(event.target.value)} /></div>
            </div>
            {selectedStock && (
              <Card className="p-3 text-sm text-muted-foreground">
                Actual: {selectedStock.cantidad_disponible ?? 0} disponible(s), {selectedStock.cantidad_reservada ?? 0} reservado(s), {selectedStock.cantidad_defectuosa ?? 0} defectuoso(s).
              </Card>
            )}
            <div className="space-y-2">
              <Label>Motivo obligatorio</Label>
              <Textarea value={stockReason} onChange={event => setStockReason(event.target.value)} placeholder="Ej. Corrección por conteo físico validado..." />
            </div>
            <Button onClick={confirmAdjustStock} disabled={submitting}>Aplicar ajuste de stock</Button>
          </TabsContent>

          <TabsContent value="orders" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Orden</Label>
                <Input value={orderSearch} onChange={event => { setOrderSearch(event.target.value); setOrderId('') }} placeholder="Buscar por orden, cliente, teléfono o estado" />
                <div className="max-h-40 overflow-y-auto rounded-md border p-1">
                  {filteredOrders.length === 0 ? (
                    <p className="px-2 py-1.5 text-xs text-muted-foreground">Sin órdenes encontradas</p>
                  ) : filteredOrders.map(order => (
                    <button key={order.id} type="button" className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-muted" onClick={() => selectOrder(order)}>
                      <span className="truncate">#{order.id} · {order.customer_name}</span>
                      <Badge variant="secondary">{order.estado}</Badge>
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label>Método de pago</Label>
                <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                  <SelectTrigger><SelectValue placeholder="Sin cambio" /></SelectTrigger>
                  <SelectContent>{paymentMethods.map(method => <SelectItem key={method} value={method}>{method}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2"><Label>Banco transferencia</Label><Input value={transferBankName} onChange={event => setTransferBankName(event.target.value)} /></div>
              <div className="space-y-2"><Label>Referencia transferencia</Label><Input value={transferReference} onChange={event => setTransferReference(event.target.value)} /></div>
            </div>
            <div className="space-y-3 rounded-md border p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <Label>Desglose mixto opcional</Label>
                  <p className="text-xs text-muted-foreground">Usa filas estructuradas para corregir montos por método.</p>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={() => setPaymentLines(previous => [...previous, createPaymentLine()])}>
                  <Plus size={16} className="mr-1" /> Agregar pago
                </Button>
              </div>
              {paymentLines.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin desglose mixto. Puedes corregir solo método, banco o referencia.</p>
              ) : paymentLines.map(line => (
                <div key={line.id} className="grid gap-2 md:grid-cols-[160px_140px_1fr_1fr_auto] md:items-end">
                  <div className="space-y-1.5">
                    <Label>Método</Label>
                    <Select value={line.method} onValueChange={value => updatePaymentLine(line.id, { method: value as PaymentMethod })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>{paymentMethods.map(method => <SelectItem key={method} value={method}>{paymentMethodLabels[method]}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5"><Label>Monto</Label><Input type="number" min="0" step="0.01" value={line.amount} onChange={event => updatePaymentLine(line.id, { amount: event.target.value })} /></div>
                  <div className="space-y-1.5"><Label>Banco</Label><Input value={line.bank_name} onChange={event => updatePaymentLine(line.id, { bank_name: event.target.value })} disabled={line.method !== 'transferencia'} /></div>
                  <div className="space-y-1.5"><Label>Referencia</Label><Input value={line.reference} onChange={event => updatePaymentLine(line.id, { reference: event.target.value })} disabled={line.method !== 'transferencia'} /></div>
                  <Button type="button" variant="outline" size="icon" onClick={() => removePaymentLine(line.id)} title="Quitar pago">
                    <Trash size={16} />
                  </Button>
                </div>
              ))}
              {selectedOrder && paymentLines.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge variant="secondary">Orden: {selectedOrderTotal.toLocaleString('es-HN', { minimumFractionDigits: 2 })}</Badge>
                  <Badge variant={Math.abs(paymentDifference) < 0.01 ? 'default' : 'destructive'}>
                    Diferencia: {paymentDifference.toLocaleString('es-HN', { minimumFractionDigits: 2 })}
                  </Badge>
                </div>
              )}
            </div>
            <div className="space-y-2"><Label>Notas de corrección</Label><Input value={paymentNotes} onChange={event => setPaymentNotes(event.target.value)} /></div>
            <div className="space-y-2"><Label>Motivo obligatorio</Label><Textarea value={orderReason} onChange={event => setOrderReason(event.target.value)} /></div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={confirmCorrectPayment} disabled={submitting}><CreditCard size={16} className="mr-2" />Corregir pago</Button>
              <Button variant="destructive" onClick={confirmCancelOrder} disabled={submitting}>Cancelar orden y devolver stock</Button>
            </div>
          </TabsContent>

          <TabsContent value="transfers" className="space-y-4">
            <div className="space-y-2">
              <Label>Transferencia pendiente</Label>
              <Input value={transferSearch} onChange={event => { setTransferSearch(event.target.value); setTransferId('') }} placeholder="Buscar por ID, producto, origen o destino" />
              <div className="max-h-40 overflow-y-auto rounded-md border p-1">
                {filteredTransfers.length === 0 ? (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground">Sin transferencias pendientes</p>
                ) : filteredTransfers.map(transfer => (
                  <button key={transfer.id} type="button" className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-muted" onClick={() => selectTransfer(transfer)}>
                    <span className="truncate">#{transfer.id} · {transfer.product_nombre}</span>
                    <Badge variant="secondary">{transfer.from_location_name} a {transfer.to_location_name}</Badge>
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2"><Label>Motivo obligatorio</Label><Textarea value={transferReason} onChange={event => setTransferReason(event.target.value)} /></div>
            {selectedTransfer && (
              <Card className="p-3 text-sm text-muted-foreground">
                Transferencia #{selectedTransfer.id}: {selectedTransfer.cantidad} unidad(es) de {selectedTransfer.product_nombre}.
              </Card>
            )}
            <Button variant="destructive" onClick={confirmCancelTransfer} disabled={submitting}>Cancelar transferencia pendiente</Button>
          </TabsContent>

          <TabsContent value="products" className="space-y-4">
            <div className="space-y-2">
              <Label>Producto</Label>
              <Input value={catalogProductSearch} onChange={event => { setCatalogProductSearch(event.target.value); setCatalogProductId('') }} placeholder="Buscar producto, SKU o modelo" />
              <div className="max-h-40 overflow-y-auto rounded-md border p-1">
                {filteredCatalogProducts.map(product => (
                  <button key={product.id} type="button" className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-muted" onClick={() => selectCatalogProduct(product)}>
                    <span className="truncate">{product.nombre}</span>
                    <Badge variant="secondary">{product.sku || 'Sin SKU'}</Badge>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2"><Label>SKU</Label><Input value={catalogSku} onChange={event => setCatalogSku(event.target.value)} /></div>
              <div className="space-y-2"><Label>Nombre</Label><Input value={catalogName} onChange={event => setCatalogName(event.target.value)} /></div>
              <div className="space-y-2"><Label>Marca</Label><Input value={catalogBrand} onChange={event => setCatalogBrand(event.target.value)} /></div>
              <div className="space-y-2"><Label>Modelo</Label><Input value={catalogModel} onChange={event => setCatalogModel(event.target.value)} /></div>
              <div className="space-y-2"><Label>Color</Label><Input value={catalogColor} onChange={event => setCatalogColor(event.target.value)} /></div>
              <div className="space-y-2"><Label>Capacidad</Label><Input value={catalogCapacity} onChange={event => setCatalogCapacity(event.target.value)} /></div>
              <div className="space-y-2"><Label>Precio</Label><Input type="number" min="0" step="0.01" value={catalogPrice} onChange={event => setCatalogPrice(event.target.value)} /></div>
              <div className="space-y-2"><Label>Costo</Label><Input type="number" min="0" step="0.01" value={catalogCost} onChange={event => setCatalogCost(event.target.value)} /></div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox checked={catalogActive} onCheckedChange={checked => setCatalogActive(Boolean(checked))} />
              Producto activo
            </label>
            <div className="space-y-2"><Label>Motivo obligatorio</Label><Textarea value={catalogReason} onChange={event => setCatalogReason(event.target.value)} /></div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={confirmCorrectProduct} disabled={submitting}>Guardar corrección de producto</Button>
              {selectedCatalogProduct && Boolean(selectedCatalogProduct.is_serialized || selectedCatalogProduct.categoria === 'celular') && (
                <Button type="button" variant="outline" onClick={() => openImeiRegistry(selectedCatalogProduct)}>
                  <Barcode size={16} className="mr-2" /> Modificar IMEIs
                </Button>
              )}
            </div>
          </TabsContent>

          <TabsContent value="audit" className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1.5"><Label>Usuario</Label><Input value={auditUsername} onChange={event => setAuditUsername(event.target.value)} placeholder="usuario" /></div>
              <div className="space-y-1.5"><Label>Acción</Label><Input value={auditAction} onChange={event => setAuditAction(event.target.value)} placeholder="stock.adjust" /></div>
              <div className="space-y-1.5"><Label>Entidad</Label><Input value={auditEntityType} onChange={event => setAuditEntityType(event.target.value)} placeholder="order, product, stock" /></div>
              <div className="space-y-1.5"><Label>ID entidad</Label><Input value={auditEntityId} onChange={event => setAuditEntityId(event.target.value)} placeholder="123" /></div>
              <div className="space-y-1.5"><Label>Desde</Label><Input type="date" value={auditStartDate} onChange={event => setAuditStartDate(event.target.value)} /></div>
              <div className="space-y-1.5"><Label>Hasta</Label><Input type="date" value={auditEndDate} onChange={event => setAuditEndDate(event.target.value)} /></div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => loadAuditLogs()}>Filtrar auditoría</Button>
              <Button variant="outline" onClick={() => exportCsv('auditoria_super_admin.csv', auditLogs as unknown as Array<Record<string, unknown>>)}>Exportar CSV</Button>
            </div>
            <div className="space-y-2"><Label>Motivo para reversa</Label><Input value={auditReason} onChange={event => setAuditReason(event.target.value)} placeholder="Obligatorio si vas a revertir" /></div>
            <div className="space-y-2">
              {auditLogs.map(log => {
                const reversible = ['super_admin.stock.adjust', 'super_admin.product.catalog_correction', 'super_admin.order.payment_correction'].includes(log.action)
                return (
                  <Card key={log.id} className="p-3 space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-medium">#{log.id} · {log.action}</p>
                        <p className="text-xs text-muted-foreground">{log.username || 'Sistema'} · {new Date(log.created_at).toLocaleString('es-HN')} · {log.entity_type} #{log.entity_id || '-'}</p>
                      </div>
                      {reversible && <Button variant="destructive" size="sm" onClick={() => confirmRevertAudit(log)}>Revertir</Button>}
                    </div>
                    <div className="grid gap-2 md:grid-cols-2 text-xs">
                      <pre className="max-h-32 overflow-auto rounded bg-muted p-2">Antes: {JSON.stringify(log.before_data ?? {}, null, 2)}</pre>
                      <pre className="max-h-32 overflow-auto rounded bg-muted p-2">Después: {JSON.stringify(log.after_data ?? {}, null, 2)}</pre>
                    </div>
                  </Card>
                )
              })}
            </div>
          </TabsContent>

          <TabsContent value="history" className="space-y-4">
            <div className="grid gap-3 md:grid-cols-5">
              <div className="space-y-1.5"><Label>Tipo entidad</Label><Input value={historyFilters.entity_type} onChange={event => setHistoryFilters(current => ({ ...current, entity_type: event.target.value }))} placeholder="product/order/stock" /></div>
              <div className="space-y-1.5"><Label>ID entidad</Label><Input value={historyFilters.entity_id} onChange={event => setHistoryFilters(current => ({ ...current, entity_id: event.target.value }))} /></div>
              <div className="space-y-1.5"><Label>ID producto</Label><Input value={historyFilters.product_id} onChange={event => setHistoryFilters(current => ({ ...current, product_id: event.target.value }))} /></div>
              <div className="space-y-1.5"><Label>ID ubicación</Label><Input value={historyFilters.location_id} onChange={event => setHistoryFilters(current => ({ ...current, location_id: event.target.value }))} /></div>
              <div className="space-y-1.5"><Label>IMEI</Label><Input value={historyFilters.imei} onChange={event => setHistoryFilters(current => ({ ...current, imei: event.target.value }))} /></div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => loadEntityHistory()}>Cargar historial</Button>
              <Button variant="outline" onClick={() => exportCsv('historial_entidad_stock.csv', entityHistory.stock_history as unknown as Array<Record<string, unknown>>)}>Stock CSV</Button>
              <Button variant="outline" onClick={() => exportCsv('historial_entidad_imeis.csv', entityHistory.imei_history as unknown as Array<Record<string, unknown>>)}>IMEI CSV</Button>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <Card className="p-3"><p className="font-medium mb-2">Auditoría</p>{entityHistory.audit_logs.slice(0, 10).map(item => <p key={item.id} className="text-xs text-muted-foreground">#{item.id} · {item.action}</p>)}</Card>
              <Card className="p-3"><p className="font-medium mb-2">Stock</p>{entityHistory.stock_history.slice(0, 10).map(item => <p key={item.id} className="text-xs text-muted-foreground">{item.tipo_cambio} · {item.stock_anterior} a {item.stock_nuevo}</p>)}</Card>
              <Card className="p-3"><p className="font-medium mb-2">IMEIs</p>{entityHistory.imei_history.slice(0, 10).map(item => <p key={item.id} className="text-xs text-muted-foreground">{item.imei} · {item.event_type}</p>)}</Card>
            </div>
          </TabsContent>

          <TabsContent value="alerts" className="space-y-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="space-y-1.5"><Label>Días transferencia pendiente</Label><Input type="number" min="1" value={staleTransferDays} onChange={event => setStaleTransferDays(event.target.value)} className="w-32" /></div>
              <Button variant="outline" onClick={loadAlerts}>Actualizar alertas</Button>
              <Button variant="outline" onClick={() => exportCsv('alertas_super_admin.csv', alerts as unknown as Array<Record<string, unknown>>)}>Exportar CSV</Button>
            </div>
            {alerts.length === 0 ? <Card className="p-4 text-sm text-muted-foreground">No hay alertas activas.</Card> : alerts.map(alert => (
              <Card key={alert.id} className="p-3 flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{alert.title}</p>
                  <p className="text-sm text-muted-foreground">{alert.detail}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={alert.severity === 'alta' ? 'destructive' : 'secondary'}>{alert.severity}</Badge>
                  <Button variant="outline" size="sm" onClick={() => investigateAlert(alert)}>Investigar</Button>
                </div>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="users" className="space-y-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="space-y-1.5 flex-1 min-w-64"><Label>Buscar usuario</Label><Input value={userSearch} onChange={event => setUserSearch(event.target.value)} placeholder="usuario, nombre o email" /></div>
              <Button variant="outline" onClick={loadUsers}>Buscar</Button>
              <Button variant="outline" onClick={() => exportCsv('usuarios_super_admin.csv', adminUsers as unknown as Array<Record<string, unknown>>)}>CSV</Button>
            </div>
            <div className="space-y-2"><Label>Motivo para acción de usuario</Label><Input value={userReason} onChange={event => setUserReason(event.target.value)} /></div>
            <div className="grid gap-3 md:grid-cols-2">
              {adminUsers.map(user => (
                <Card key={user.id} className={`p-3 space-y-2 ${selectedUserId === String(user.id) ? 'ring-2 ring-primary' : ''}`}>
                  <button type="button" className="w-full text-left" onClick={() => setSelectedUserId(String(user.id))}>
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">{user.full_name || user.username}</p>
                      <Badge variant={user.is_active ? 'default' : 'destructive'}>{user.is_active ? 'Activo' : 'Bloqueado'}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{user.username} · {user.role_name || 'Sin rol'} · {user.audit_action_count} acción(es)</p>
                    <p className="text-xs text-muted-foreground">Última acción: {user.last_action || 'Sin actividad'}</p>
                  </button>
                  {selectedUserId === String(user.id) && (
                    <div className="flex flex-wrap gap-2">
                      <Button variant="outline" size="sm" onClick={() => confirmSetUserActive(!user.is_active)}>{user.is_active ? 'Bloquear' : 'Activar'}</Button>
                      <Button variant="destructive" size="sm" onClick={confirmResetUserRole}>Resetear rol</Button>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="reports" className="space-y-4">
            <Card className="p-4 space-y-3">
              <h3 className="font-semibold">Exportaciones operativas</h3>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => exportCsv('auditoria_super_admin.csv', auditLogs as unknown as Array<Record<string, unknown>>)}>Auditoría CSV</Button>
                <Button variant="outline" onClick={() => exportCsv('diagnostico_stock_imeis.csv', issues as unknown as Array<Record<string, unknown>>)}>Inconsistencias CSV</Button>
                <Button variant="outline" onClick={() => exportCsv('alertas_super_admin.csv', alerts as unknown as Array<Record<string, unknown>>)}>Alertas CSV</Button>
                <Button variant="outline" onClick={() => window.print()}>Imprimir / PDF</Button>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(pendingConfirmation)} onOpenChange={open => !open && setPendingConfirmation(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{pendingConfirmation?.title}</AlertDialogTitle>
            <AlertDialogDescription>{pendingConfirmation?.description}</AlertDialogDescription>
          </AlertDialogHeader>
          {pendingConfirmation?.requiredText && (
            <div className="space-y-2">
              <Label>Escribe {pendingConfirmation.requiredText} para continuar</Label>
              <Input value={confirmText} onChange={event => setConfirmText(event.target.value)} autoFocus />
            </div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={submitting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={submitting || Boolean(pendingConfirmation?.requiredText && confirmText !== pendingConfirmation.requiredText)}
              onClick={event => {
                event.preventDefault()
                void runPendingConfirmation()
              }}
              className={pendingConfirmation?.dangerous ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90' : undefined}
            >
              {submitting ? 'Aplicando...' : pendingConfirmation?.confirmLabel}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {imeiRegistryProduct && (
        <ProductIMEIRegistryDialog
          open={Boolean(imeiRegistryProduct)}
          onOpenChange={open => !open && setImeiRegistryProduct(null)}
          product={imeiRegistryProduct}
          allowAdminActions
          locations={activeLocations}
          onUpdated={refreshPanelData}
        />
      )}
    </>
  )
}
