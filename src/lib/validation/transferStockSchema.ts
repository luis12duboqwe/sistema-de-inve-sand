import { z } from 'zod'
import type { ProductWithStock } from '@/lib/types'

const normalizeId = (label: string) =>
  z.preprocess(
    value => {
      if (typeof value === 'string') {
        const trimmed = value.trim()
        if (trimmed === '') {
          return undefined
        }
        const parsed = Number(trimmed)
        return Number.isNaN(parsed) ? undefined : parsed
      }
      if (typeof value === 'number') {
        return Number.isNaN(value) ? undefined : value
      }
      return undefined
    },
    z
      .number({
        required_error: `Selecciona ${label}`
      })
      .int({
        message: `Selecciona ${label}`
      })
      .positive({
        message: `Selecciona ${label}`
      })
  )

const cantidadSchema = z.preprocess(
  value => {
    if (typeof value === 'number') {
      return value
    }
    if (typeof value === 'string' && value.trim() !== '') {
      const parsed = Number(value)
      return Number.isNaN(parsed) ? undefined : parsed
    }
    return undefined
  },
  z
    .number({ required_error: 'Ingresa la cantidad a transferir' })
    .int({ message: 'La cantidad debe ser un número entero' })
    .min(1, { message: 'La cantidad debe ser mayor a 0' })
)

const notasSchema = z
  .string()
  .max(500, { message: 'Las notas no pueden exceder 500 caracteres' })
  .optional()
  .or(z.literal('').transform(() => undefined))

export const createTransferStockSchema = (product: ProductWithStock | null | undefined) =>
  z
    .object({
      fromLocationId: normalizeId('la ubicación de origen'),
      toLocationId: normalizeId('la ubicación de destino'),
      cantidad: cantidadSchema,
      notas: notasSchema
    })
    .superRefine((data, ctx) => {
      if (data.fromLocationId === data.toLocationId) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'La ubicación destino debe ser diferente a la de origen',
          path: ['toLocationId']
        })
      }

      if (!product) {
        return
      }

      const stockItem = product.stock_items?.find(s => s.location_id === data.fromLocationId)
      const disponible = stockItem?.cantidad_disponible ?? 0
      const reservado = stockItem?.cantidad_reservada ?? 0
      const stockLibre = Math.max(disponible - reservado, 0)

      if (stockLibre <= 0) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'No hay stock disponible en la ubicación seleccionada',
          path: ['fromLocationId']
        })
        return
      }

      if (data.cantidad > stockLibre) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Solo hay ${stockLibre} unidades disponibles en la ubicación origen`,
          path: ['cantidad']
        })
      }
    })

export type TransferStockFormValues = z.infer<ReturnType<typeof createTransferStockSchema>>
