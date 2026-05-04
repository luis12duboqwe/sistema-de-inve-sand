import { z } from 'zod'
import { validatePhoneNumber } from '@/lib/phoneValidator'
import type { ProductWithStock, Bank, TradeIn } from '@/lib/types'
import type { ValidationIssue, ValidationResult } from './types'

export interface OrderItemDraft {
  product_id: number
  cantidad: number
  imeis?: string[]
  precio_unitario?: number
}

export interface OrderFormDraft {
  salesProfileSlug: string
  sourceLocationId: number | null
  customerName: string
  customerPhone: string
  canal: 'whatsapp' | 'facebook' | 'instagram' | 'tienda'
  metodoPago: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  transferBankName?: string
  transferReference?: string
  items: OrderItemDraft[]
  tradeIns: (TradeIn & { valor_estimado: number })[]
  notas?: string
  deliveryDate?: string
  cashDownPayment?: string
  selectedBankId: number | null
  selectedMonths: number | null
}

export interface OrderValidationContext {
  products: ProductWithStock[]
  banks: Bank[]
}

export const ORDER_FIELD_LIMITS = {
  MAX_CUSTOMER_NAME_LENGTH: 200,
  MAX_PHONE_LENGTH: 20,
  MAX_ORDER_NOTES_LENGTH: 1000,
  MAX_TRADE_IN_NOTES_LENGTH: 500
}

const numericFieldSchema = (
  requiredMessage: string,
  invalidMessage: string,
  minValue?: number,
  minMessage?: string
) =>
  z.preprocess(
    value => {
      if (value === undefined || value === null || value === '') return undefined
      if (typeof value === 'number') return value

      let normalized = String(value).trim().replace(/\s+/g, '')
      if (!normalized) return undefined

      if (normalized.includes(',') && normalized.includes('.')) {
        if (normalized.lastIndexOf(',') > normalized.lastIndexOf('.')) {
          normalized = normalized.replace(/\./g, '').replace(',', '.')
        } else {
          normalized = normalized.replace(/,/g, '')
        }
      } else if (normalized.includes(',')) {
        normalized = normalized.replace(',', '.')
      }

      const parsed = Number(normalized)
      return Number.isNaN(parsed) ? value : parsed
    },
    z.number({ required_error: requiredMessage, invalid_type_error: invalidMessage }).refine(
      value => (minValue === undefined ? true : value >= minValue),
      { message: minMessage ?? `El valor debe ser mayor o igual a ${minValue ?? 0}` }
    )
  )

const locationSchema = z.preprocess(
  value => {
    if (value === null || value === undefined) return undefined
    const parsed = Number(value)
    return Number.isNaN(parsed) ? undefined : parsed
  },
  z
    .number({ required_error: 'Selecciona una ubicación origen' })
    .int({ message: 'Selecciona una ubicación origen' })
    .positive({ message: 'Selecciona una ubicación origen' })
)

const bankIdSchema = z
  .number()
  .int()
  .positive()
  .nullable()

const monthsSchema = z
  .number()
  .int()
  .positive()
  .nullable()

const orderItemSchema = z.object({
  product_id: z
    .number({ required_error: 'Selecciona un producto' })
    .int({ message: 'Selecciona un producto válido' })
    .positive({ message: 'Selecciona un producto válido' }),
  cantidad: z
    .number({ required_error: 'Ingresa la cantidad' })
    .int({ message: 'La cantidad debe ser un entero' })
    .min(1, { message: 'La cantidad debe ser mayor a 0' }),
  imeis: z.array(z.string().trim().min(3, 'IMEI inválido')).optional(),
  precio_unitario: numericFieldSchema(
    'Ingresa el precio unitario',
    'El precio debe ser numérico',
    0,
    'El precio unitario no puede ser negativo'
  ).optional()
})

const tradeInSchema = z.object({
  marca: z.string().trim().min(1, { message: 'La marca es obligatoria' }),
  modelo: z.string().trim().min(1, { message: 'El modelo es obligatorio' }),
  color: z.string().trim().max(100).optional(),
  capacidad: z.string().trim().max(100).optional(),
  imei: z
    .string()
    .trim()
    .regex(/^[0-9]{14,17}$/u, { message: 'IMEI inválido para la retoma' })
    .optional()
    .or(z.literal('').transform(() => undefined)),
  condicion: z.enum(['usado', 'dañado', 'para_repuestos']),
  valor_estimado: z
    .number({ required_error: 'El valor estimado es obligatorio' })
    .min(0, { message: 'El valor estimado no puede ser negativo' }),
  precio_venta: z.number().min(0).optional(),
  notas: z
    .string()
    .max(ORDER_FIELD_LIMITS.MAX_TRADE_IN_NOTES_LENGTH, {
      message: `Las notas no pueden exceder ${ORDER_FIELD_LIMITS.MAX_TRADE_IN_NOTES_LENGTH} caracteres`
    })
    .optional()
})

const orderSchema = z.object({
  salesProfileSlug: z.string().trim().min(1, { message: 'Selecciona un canal de venta' }),
  sourceLocationId: locationSchema,
  customerName: z
    .string()
    .trim()
    .min(1, { message: 'Ingresa el nombre del cliente' })
    .max(ORDER_FIELD_LIMITS.MAX_CUSTOMER_NAME_LENGTH, {
      message: `El nombre no puede exceder ${ORDER_FIELD_LIMITS.MAX_CUSTOMER_NAME_LENGTH} caracteres`
    }),
  customerPhone: z
    .string()
    .trim()
    .min(1, { message: 'Ingresa el teléfono del cliente' })
    .max(ORDER_FIELD_LIMITS.MAX_PHONE_LENGTH, {
      message: `El teléfono no puede exceder ${ORDER_FIELD_LIMITS.MAX_PHONE_LENGTH} caracteres`
    })
    .refine(value => validatePhoneNumber(value).valid, {
      message: 'El teléfono del cliente es inválido'
    }),
  canal: z.enum(['whatsapp', 'facebook', 'instagram', 'tienda']),
  metodoPago: z.enum(['efectivo', 'transferencia', 'tarjeta', 'financiamiento']),
  transferBankName: z.string().trim().max(120, { message: 'El banco no puede exceder 120 caracteres' }).optional(),
  transferReference: z.string().trim().max(120, { message: 'La referencia no puede exceder 120 caracteres' }).optional(),
  items: z.array(orderItemSchema).min(1, { message: 'Agrega al menos un producto' }),
  tradeIns: z.array(tradeInSchema).optional().default([]),
  notas: z
    .string()
    .max(ORDER_FIELD_LIMITS.MAX_ORDER_NOTES_LENGTH, {
      message: `Las notas no pueden exceder ${ORDER_FIELD_LIMITS.MAX_ORDER_NOTES_LENGTH} caracteres`
    })
    .optional(),
  deliveryDate: z.string().optional(),
  cashDownPayment: z.string().optional(),
  selectedBankId: bankIdSchema,
  selectedMonths: monthsSchema
})

const sanitizeCashDownPayment = (value?: string) => {
  if (!value || value.trim() === '') return 0
  const parsed = Number(value)
  return Number.isNaN(parsed) ? NaN : parsed
}

const makeIssue = (field: string, message: string): ValidationIssue => ({ field, message })

export const validateOrderForm = (
  draft: OrderFormDraft,
  context: OrderValidationContext
): ValidationResult => {
  const parsed = orderSchema.safeParse(draft)
  if (!parsed.success) {
    const issues: ValidationIssue[] = parsed.error.issues.map(issue => {
      const path = issue.path.join('.') || 'form'
      return makeIssue(path, issue.message)
    })
    return { ok: false, issues }
  }

  const resultIssues: ValidationIssue[] = []
  const {
    sourceLocationId,
    metodoPago,
    transferBankName,
    transferReference,
    selectedBankId,
    selectedMonths,
    items,
    tradeIns,
  } = parsed.data

  if (metodoPago === 'transferencia') {
    if (!transferBankName?.trim()) {
      resultIssues.push(makeIssue('transferBankName', 'Selecciona o ingresa el banco de la transferencia'))
    }

    if (!transferReference?.trim()) {
      resultIssues.push(makeIssue('transferReference', 'Ingresa el número de referencia de la transferencia'))
    }
  }

  // Productos duplicados
  const seenProducts = new Set<number>()
  items.forEach((item, index) => {
    if (seenProducts.has(item.product_id)) {
      resultIssues.push(
        makeIssue(`items[${index}].product_id`, 'Este producto ya fue agregado. Ajusta la cantidad en la fila original.')
      )
    } else {
      seenProducts.add(item.product_id)
    }
  })

  // Validar productos y stock
  items.forEach((item, index) => {
    const product = context.products.find(p => p.id === item.product_id)
    if (!product) {
      resultIssues.push(makeIssue(`items[${index}].product_id`, 'El producto seleccionado ya no existe'))
      return
    }

    const available = (() => {
      if (!sourceLocationId) return product.stock_disponible || 0
      if (product.stock_items && product.stock_items.length > 0) {
        const stockInLocation = product.stock_items.find(s => s.location_id === sourceLocationId)
        const disponible = stockInLocation?.cantidad_disponible || 0
        const reservado = stockInLocation?.cantidad_reservada || 0
        return Math.max(disponible - reservado, 0)
      }
      return product.stock_disponible || 0
    })()

    if (available <= 0) {
      resultIssues.push(
        makeIssue(`items[${index}].product_id`, 'No hay stock disponible para este producto en la ubicación seleccionada')
      )
    }

    if (item.cantidad > available) {
      resultIssues.push(
        makeIssue(`items[${index}].cantidad`, `Solo hay ${available} unidades disponibles de "${product.nombre}"`)
      )
    }

    const isSerialized = product.is_serialized || product.categoria === 'celular'
    if (isSerialized) {
      const imeis = item.imeis || []
      if (imeis.length !== item.cantidad) {
        resultIssues.push(
          makeIssue(
            `items[${index}].imeis`,
            `Selecciona ${item.cantidad} IMEIs para "${product.nombre}"`
          )
        )
      }
    }
  })

  // Trade-ins adicionales
  tradeIns.forEach((tradeIn, index) => {
    if (tradeIn.valor_estimado < 0) {
      resultIssues.push(makeIssue(`tradeIns[${index}].valor_estimado`, 'El valor estimado no puede ser negativo'))
    }
    if (tradeIn.precio_venta !== undefined && tradeIn.precio_venta < 0) {
      resultIssues.push(makeIssue(`tradeIns[${index}].precio_venta`, 'El precio de venta sugerido no puede ser negativo'))
    }
  })

  const downPayment = sanitizeCashDownPayment(parsed.data.cashDownPayment)
  if (Number.isNaN(downPayment)) {
    resultIssues.push(makeIssue('cashDownPayment', 'La prima debe ser un valor numérico válido'))
  } else if (downPayment < 0) {
    resultIssues.push(makeIssue('cashDownPayment', 'La prima o pago inicial no puede ser negativa'))
  }

  const bank = selectedBankId ? context.banks.find(b => b.id === selectedBankId) : null
  if (metodoPago === 'financiamiento') {
    if (!selectedBankId) {
      resultIssues.push(makeIssue('selectedBankId', 'Selecciona el banco para el financiamiento'))
    }
    if (!selectedMonths) {
      resultIssues.push(makeIssue('selectedMonths', 'Selecciona el plazo del financiamiento'))
    }
    if (selectedBankId && !bank) {
      resultIssues.push(makeIssue('selectedBankId', 'El banco seleccionado ya no está disponible'))
    }
    if (selectedMonths && bank) {
      const hasOption = bank.financing_options?.some(option => option.months === selectedMonths)
      if (!hasOption) {
        resultIssues.push(makeIssue('selectedMonths', 'El banco no ofrece el plazo seleccionado'))
      }
    }
  } else if (metodoPago === 'tarjeta') {
    if (!selectedBankId) {
      resultIssues.push(makeIssue('selectedBankId', 'Selecciona el banco para el cobro con tarjeta'))
    } else if (!bank) {
      resultIssues.push(makeIssue('selectedBankId', 'El banco seleccionado ya no está disponible'))
    }
  }

  if (resultIssues.length > 0) {
    return { ok: false, issues: resultIssues }
  }

  return { ok: true, issues: [] }
}
