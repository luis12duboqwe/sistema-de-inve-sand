# Guía de Integración con n8n - Sistema de Inteligencia de Ventas

Esta guía explica cómo conectar tu flujo de trabajo de n8n con el Sistema de Inventario Multi-Ubicación para habilitar las capacidades de IA.

## Visión General

El sistema expone una API dedicada en `/api/ai/*` diseñada específicamente para ser consumida por agentes de IA (n8n, LangChain, Flowise).

El flujo general es:
1. **Recibir Mensaje**: n8n recibe un mensaje de WhatsApp/Facebook/Instagram.
2. **Obtener Contexto**: n8n consulta al sistema (`/api/ai/context`) para obtener el "cerebro" del bot actual (prompt, inventario, historial).
3. **Generar Respuesta**: n8n envía el contexto + mensaje del usuario a OpenAI/Anthropic.
4. **Registrar Interacción**: n8n guarda la conversación en el sistema (`/api/ai/log-interaction`) para análisis futuro.
5. **Manejo de Excepciones**: Si la IA no sabe la respuesta, n8n puede enviarla a la cola de entrenamiento (`/api/ai/training-queue`).

## Endpoints de la API

### 1. Obtener Contexto ("El Cerebro")
Este es el endpoint más importante. Devuelve todo lo que la IA necesita saber para responder.

- **URL**: `POST /api/ai/context`
- **Body**:
  ```json
  {
    "sales_profile_id": 1,       // ID del perfil (bot) que está respondiendo
    "customer_phone": "50499998888", // Teléfono del cliente (para buscar historial)
    "customer_name": "Juan Perez",   // Opcional, si se conoce
    "query": "Tienen iPhone 13?"     // La pregunta del usuario (para búsqueda semántica futura)
  }
  ```
- **Respuesta**:
  ```json
  {
    "system_prompt": "Eres 'Vendedor Estrella', un asistente amable...", // Personalidad configurada
    "inventory_context": "Inventario disponible: iPhone 13 (5 unids) - $800...", // Resumen de stock
    "customer_context": "Cliente VIP. Última compra: hace 2 días.", // Historial CRM
    "recent_interactions": [...] // Últimos 5 mensajes para mantener el hilo
  }
  ```

### 2. Registrar Interacción
Guarda el historial para que el sistema aprenda y para mostrarlo en "Insights de Clientes".

- **URL**: `POST /api/ai/log-interaction`
- **Body**:
  ```json
  {
    "sales_profile_id": 1,
    "customer_phone": "50499998888",
    "message_content": "Sí, tenemos iPhone 13 en azul.",
    "message_source": "ai", // 'user' o 'ai'
    "platform": "whatsapp"
  }
  ```

### 3. Cola de Entrenamiento
Si la IA detecta que no puede responder o el usuario pide un humano.

- **URL**: `POST /api/ai/training-queue`
- **Body**:
  ```json
  {
    "sales_profile_id": 1,
    "question": "¿Aceptan Bitcoin?",
    "original_answer": "Lo siento, no estoy seguro.", // Opcional
    "confidence_score": 0.4 // Opcional
  }
  ```

## Ejemplo de Flujo en n8n

### Paso 1: Webhook (WhatsApp)
Recibe el mensaje entrante.
- Output: `body.from`, `body.text.body`

### Paso 2: HTTP Request (Get Context)
- **Method**: POST
- **URL**: `https://tu-api.com/api/ai/context`
- **Body**:
  ```json
  {
    "sales_profile_id": 1,
    "customer_phone": "={{ $json.body.from }}",
    "query": "={{ $json.body.text.body }}"
  }
  ```

### Paso 3: OpenAI (Chat Model)
- **System Message**: `={{ $node["Get Context"].json.system_prompt }}`
- **User Message**:
  ```text
  Contexto del Inventario:
  {{ $node["Get Context"].json.inventory_context }}

  Contexto del Cliente:
  {{ $node["Get Context"].json.customer_context }}

  Mensaje del Usuario:
  {{ $json.body.text.body }}
  ```

### Paso 4: HTTP Request (Log User Message)
Registra lo que dijo el usuario.
- **URL**: `/api/ai/log-interaction`
- **Body**: `source: "user"`

### Paso 5: HTTP Request (Log AI Response)
Registra lo que respondió la IA.
- **URL**: `/api/ai/log-interaction`
- **Body**: `source: "ai"`, `content: ={{ $node["OpenAI"].json.content }}`

### Paso 6: Webhook Response (WhatsApp)
Envía la respuesta al usuario.

## Configuración de Perfiles

Para que esto funcione, debes configurar tus perfiles en el sistema:
1. Ve a la pestaña **Canales**.
2. Haz clic en el botón **IA** en la tarjeta del perfil.
3. Define el **Prompt del Sistema** (Personalidad).
4. Activa las opciones de inventario/precios según lo que quieras que la IA sepa.

## Seguridad

Actualmente, la API es pública si se despliega sin autenticación adicional. Se recomienda:
1. Implementar Basic Auth o Bearer Token en `backend/app/main.py` si se expone a internet.
2. O usar un túnel seguro / VPN entre n8n y el servidor.
