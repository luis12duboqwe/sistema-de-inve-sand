import { inventoryServiceInstance } from './inventoryServiceFactory'
import type {
  AICreateOrderItemPayload,
  AICreateOrderResponse,
  AIHandleMessagePayload,
  AIHandleMessageResponse,
} from './types'

export type ChatMessageInput = {
  salesProfileSlug: string
  customerPhone: string
  messageContent: string
  customerName?: string
  channelHint?: 'whatsapp' | 'facebook' | 'instagram' | 'messenger'
  messageId?: string
  conversationOverride?: Array<Record<string, string>>
}

export type ChatOrderIntentInput = {
  sourceLocationId: number
  items: AICreateOrderItemPayload[]
  canal?: 'whatsapp' | 'facebook' | 'instagram' | 'tienda'
  metodoPago?: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  notes?: string
  autoLinkInteraction?: boolean
}

export type ChatSendResult = {
  reply: string
  tokensUsed: number
  model: string
  order?: AICreateOrderResponse
  raw: AIHandleMessageResponse
}

function normalizePhone(value: string): string {
  return String(value || '').trim()
}

function buildMessageId(prefix = 'msg'): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }

  const random = Math.random().toString(36).slice(2)
  const ts = Date.now().toString(36)
  return `${prefix}-${ts}-${random}`
}

function toHandlePayload(
  message: ChatMessageInput,
  orderIntent?: ChatOrderIntentInput
): AIHandleMessagePayload {
  const payload: AIHandleMessagePayload = {
    sales_profile_slug: message.salesProfileSlug,
    customer_phone: normalizePhone(message.customerPhone),
    customer_name: message.customerName,
    message_content: message.messageContent,
    message_id: message.messageId || buildMessageId('chat'),
    channel_hint: message.channelHint || 'whatsapp',
    conversation_override: message.conversationOverride,
  }

  if (orderIntent) {
    payload.order_intent = {
      source_location_id: orderIntent.sourceLocationId,
      items: orderIntent.items,
      canal: orderIntent.canal ?? 'whatsapp',
      metodo_pago: orderIntent.metodoPago ?? 'efectivo',
      notes: orderIntent.notes,
      auto_create: true,
      auto_link_interaction: orderIntent.autoLinkInteraction ?? true,
    }
  }

  return payload
}

export async function sendChatMessage(message: ChatMessageInput): Promise<ChatSendResult> {
  const payload = toHandlePayload(message)
  const response = await inventoryServiceInstance.handleAIMessage(payload)

  return {
    reply: response.reply,
    tokensUsed: response.tokens_used,
    model: response.model,
    order: response.order,
    raw: response,
  }
}

export async function sendChatMessageAndCreateOrder(
  message: ChatMessageInput,
  orderIntent: ChatOrderIntentInput
): Promise<ChatSendResult> {
  if (!orderIntent.items || orderIntent.items.length === 0) {
    throw new Error('Debe enviar al menos un item para crear la orden desde chat.')
  }

  const payload = toHandlePayload(message, orderIntent)
  const response = await inventoryServiceInstance.handleAIMessage(payload)

  return {
    reply: response.reply,
    tokensUsed: response.tokens_used,
    model: response.model,
    order: response.order,
    raw: response,
  }
}
