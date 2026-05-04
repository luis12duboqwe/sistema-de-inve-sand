# Prueba de Simulación n8n

He creado un script de Python que simula exactamente cómo n8n interactuará con tu sistema. Este script prueba todo el flujo de inteligencia artificial sin necesidad de configurar n8n todavía.

## Cómo ejecutar la prueba

1. Abre una terminal en VS Code.
2. Ejecuta el siguiente comando:

```bash
python3 test_n8n_simulation.py
```

## Qué hace esta prueba

1. **Busca un Bot**: Encuentra automáticamente el primer perfil de venta tipo "Bot IA" en tu base de datos.
2. **Simula un Cliente**: Crea un cliente ficticio ("Cliente de Prueba") con el número `50499998888`.
3. **Pide Contexto (`/api/ai/context`)**: Envía el mensaje "Hola, tienen iPhone 13 disponible?" y muestra lo que el "Cerebro" responde (Inventario, Prompt, etc.).
4. **Guarda Logs (`/api/ai/log`)**: Registra la conversación en la base de datos.
5. **Prueba Entrenamiento (`/api/ai/training/submit`)**: Envía una pregunta difícil ("¿Aceptan criptomonedas?") a la cola de revisión.
6. **Flujo Unificado (`/api/ai/handle-message`)**: Responde, registra conversación y opcionalmente crea orden en una sola llamada.

## Autenticación para n8n

Si tu backend tiene integración protegida, exporta el token antes de correr la simulación:

```bash
export N8N_AUTH_TOKEN="tu-token-seguro"
python3 test_n8n_simulation.py
```

El script enviará `X-N8N-Token` automáticamente cuando exista esa variable.

## Endpoint recomendado para operar sin n8n

Usa una sola llamada para conversación y cierre de venta:

`POST /api/ai/handle-message`

Payload mínimo:

```json
{
	"sales_profile_slug": "bot-whatsapp",
	"customer_phone": "50499998888",
	"customer_name": "Cliente Demo",
	"message_content": "Confirmo la compra",
	"order_intent": {
		"source_location_id": 1,
		"canal": "whatsapp",
		"metodo_pago": "efectivo",
		"items": [
			{
				"product_query": "iPhone 13",
				"cantidad": 1
			}
		],
		"auto_create": true,
		"auto_link_interaction": true
	}
}
```

Para productos serializados incluye `imeis` por item.

## Uso directo en frontend (sin n8n)

Puedes usar el orquestador en `src/lib/chatOrchestrator.ts`:

```ts
import { sendChatMessage, sendChatMessageAndCreateOrder } from '@/lib/chatOrchestrator'

const chatResult = await sendChatMessage({
	salesProfileSlug: 'bot-whatsapp',
	customerPhone: '50499998888',
	customerName: 'Cliente Demo',
	messageContent: 'Hola, qué modelos tienen?'
})

const saleResult = await sendChatMessageAndCreateOrder(
	{
		salesProfileSlug: 'bot-whatsapp',
		customerPhone: '50499998888',
		customerName: 'Cliente Demo',
		messageContent: 'Confirmo la compra'
	},
	{
		sourceLocationId: 1,
		items: [{ product_query: 'iPhone 13', cantidad: 1 }]
	}
)
```

## Resultados Esperados

Si todo está bien, verás mensajes con ✅ verde indicando que cada paso funcionó.

Después de correr la prueba, puedes ir al **Centro de Entrenamiento** en la web y verás la pregunta sobre criptomonedas pendiente de revisión.
