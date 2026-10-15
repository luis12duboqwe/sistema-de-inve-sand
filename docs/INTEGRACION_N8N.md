# n8n ↔ SoftMobile — contrato de integración (borrador)

Este documento cubre la comunicación con la API, **no certifica entrega efectiva de WhatsApp, Messenger o Instagram**.

## Prerrequisitos
- Habilitar `ENABLE_AI_FEATURES` solamente cuando el servicio tenga credenciales, permisos y política de límites; de lo contrario mantenerlo inactivo.
- Configurar `N8N_AUTH_TOKEN` o credencial de servicio permitida por `_require_ai_integration_auth` sin incluirla en el repositorio.
- Los webhooks de Meta requieren firma HMAC de la petición: el *verify token* sirve sólo para el desafío GET de alta y **no autentica eventos POST**.
- Mantener n8n y API detrás de HTTPS; no registrar teléfonos, JWT ni secretos en logs.
- La cuenta/perfil de ventas y sucursal se deben verificar de extremo a extremo.
- Nunca volver a enviar un POST que pudiera haber creado una venta o enviado un mensaje sin antes conciliar el resultado.

## Endpoints de IA (vía API protegida)

### Contexto
`POST /api/ai/context`
```json
{"sales_profile_slug":"bot-whatsapp","customer_phone":"50470000000","customer_name":"Cliente","message_content":"¿Hay iPhone disponible?"}
```

### Respuesta del bot
`POST /api/ai/reply`: mismo payload base; el backend responde con `reply`, `model`, `tokens_used` y `context`. No implica entrega a Meta.

### Mensaje idempotente
`POST /api/ai/handle-message`: payload de respuesta más `message_id` estable del canal y `channel_hint`. Los mensajes duplicados o de resultado ambiguo pueden requerir conciliación manual (HTTP 409). La respuesta no se debe copiar al historial de otro cliente.

### Entrenamiento
`POST /api/ai/training/submit`
```json
{"sales_profile_slug":"bot-whatsapp","customer_question":"¿Cuánto tarda la entrega?","ai_proposed_answer":"Consultar con un agente"}
```
El endpoint `GET /api/ai/training-queue` es para consultar la cola, no para crear ejemplos mediante POST.

### Webhooks Meta
`GET /api/channels/{whatsapp|messenger|instagram}/webhook`: validación del desafío con token.
`POST /api/channels/{whatsapp|messenger|instagram}/webhook`: petición con firma HMAC validada antes de procesar. No confundir ambos controles.

## Ejemplo n8n
[docs/n8n/whatsapp_ai_flow.json](n8n/whatsapp_ai_flow.json) es un borrador de respuesta HTTP al **webhook de n8n**. El nodo *Respond to Webhook* **no envía un mensaje por Meta**. Requiere agregar el envío oficial al proveedor, verificar permisos, registrar delivery IDs, limitar reintentos y probar con una cuenta de prueba antes de habilitarlo para clientes.

No activar automáticamente el flujo con tráfico real mientras falten esas pruebas.
