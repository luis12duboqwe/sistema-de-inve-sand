# Guía de Integración con n8n - Sistema de Inteligencia de Ventas

Esta guía explica cómo conectar tu flujo de trabajo de n8n con el Sistema de Inventario Multi-Ubicación para habilitar las capacidades de IA.

## Visión General

El sistema expone una API dedicada en `/api/ai/*` diseñada específicamente para ser consumida por agentes de IA (n8n, LangChain, Flowise).

El flujo general ahora se apalanca completamente en la API propia (sin llamadas directas a OpenAI desde n8n):
1. **Recibir Mensaje**: n8n recibe un mensaje de WhatsApp/Facebook/Instagram.
2. **Obtener Contexto**: n8n consulta al sistema (`POST /api/ai/context`) para obtener el "cerebro" del bot actual (prompt, inventario, historial).
3. **Generar Respuesta**: n8n delega la respuesta al backend (`POST /api/ai/reply`), que usa OpenAI oficial y registra la conversación automáticamente.
4. **Registrar Interacción Opcional**: Los logs se crean desde `/api/ai/reply`, pero puedes añadir anotaciones manuales vía `/api/ai/log` si el flujo lo requiere.
5. **Manejo de Excepciones**: Si la IA no sabe la respuesta, n8n puede enviarla a la cola de entrenamiento (`POST /api/ai/training-queue`).

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

- **URL**: `POST /api/ai/log`
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
### 4. Generar Respuesta (OpenAI administrado por backend)
Centraliza el llamado al modelo y el guardado del historial.

- **URL**: `POST /api/ai/reply`
- **Body**:
  ```json
  {
    "sales_profile_slug": "bot-whatsapp",
    "customer_phone": "50499998888",
    "customer_name": "Juan Perez",
    "message_content": "Hola, tienen iPhone 13?",
    "conversation_override": [
      { "role": "user", "content": "Hola" },
      { "role": "assistant", "content": "Bienvenido" }
    ]
  }
  ```
- **Respuesta**:
  ```json
  {
    "reply": "Sí, tenemos iPhone 13 en azul y negro.",
    "tokens_used": 324,
    "model": "gpt-4o-mini",
    "context": { "bot_config": { "model": "gpt-4o-mini" }, "relevant_inventory": "..." }
  }
  ```
- **Notas**:
  - Este endpoint registra automáticamente los mensajes de usuario y de la IA en `InteractionLog`.
  - Requiere las variables `ENABLE_AI_FEATURES=true` y `OPENAI_API_KEY` configuradas en el backend.
  - Úsalo con `N8N_AUTH_TOKEN` o un token Bearer de servicio si expones la API a internet.

    "sales_profile_id": 1,
    "question": "¿Aceptan Bitcoin?",
### Paso 1: Webhook (WhatsApp)
Recibe el mensaje entrante.
- Output: `body.from`, `body.text.body`

### Paso 2: HTTP Request (Get Context)
- **Method**: POST
- **URL**: `https://tu-api.com/api/ai/context`
- **Body**:
  ```json
  {
    "sales_profile_slug": "bot-whatsapp",
    "customer_phone": "={{ $json.body.from }}",
    "customer_name": "={{ $json.body.profile?.name || "" }}",
    "message_content": "={{ $json.body.text.body }}"
  }
  ```

### Paso 3: HTTP Request (AI Reply)
- **Method**: POST
- **URL**: `https://tu-api.com/api/ai/reply`
- **Body**:
  ```json
  {
    "sales_profile_slug": "bot-whatsapp",
    "customer_phone": "={{ $json.body.from }}",
    "customer_name": "={{ $json.body.profile?.name || "" }}",
    "message_content": "={{ $json.body.text.body }}"
  }
  ```
- ✅ Respuesta incluye `reply`, `tokens_used` y todo el `context` que usó el modelo.
- ✅ No necesitas llamar a OpenAI ni registrar logs manualmente (el backend lo hace).

### Paso 4: (Opcional) HTTP Request (Log Extra)
Si quieres añadir metadatos adicionales (por ejemplo, clasificación de intención), usa `/api/ai/log`.

### Paso 5: HTTP Request (Training Queue)
Cuando la IA no tenga respuesta de calidad, envía el mensaje a `/api/ai/training-queue`.

### Paso 6: Webhook Response (WhatsApp)
Envía `{{$node["AI Reply"].json.reply}}` al usuario.

> 💡 **Plantilla lista para importar**: usa `docs/n8n/whatsapp_ai_flow.json` para crear el workflow completo (inlcuye nodos de contexto, reply, logging y training). Solo debes configurar `BASE_API_URL`, `N8N_AUTH_TOKEN` y el `sales_profile_slug`.
### Paso 5: HTTP Request (Log AI Response)
Registra lo que respondió la IA.
- **URL**: `/api/ai/log`
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
1. Implementar Basic Auth o Bearer Token en `backend/app/main.py` si se expone a internet. Define `N8N_AUTH_TOKEN` y haz que todos los requests lo envíen en `Authorization: Bearer ...`.
2. O usar un túnel seguro / VPN entre n8n y el servidor.
3. Mantener `ENABLE_AI_FEATURES=false` en entornos donde no se haya configurado el workflow.
