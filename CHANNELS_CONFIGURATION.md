# Configuración de Canales Multi-Perfil

Esta guía explica cómo configurar WhatsApp, Messenger e Instagram para múltiples marcas/tiendas usando el sistema de perfiles de venta.

## Tabla de contenidos

1. [Arquitectura](#arquitectura)
2. [Pasos rápidos](#pasos-rápidos)
3. [Obtener credenciales de Meta](#obtener-credenciales-de-meta)
4. [Cargar datos de prueba](#cargar-datos-de-prueba)
5. [Configurar en la UI](#configurar-en-la-ui)
6. [Registrar webhooks](#registrar-webhooks)
7. [Pruebas end-to-end](#pruebas-end-to-end)
8. [Solución de problemas](#solución-de-problemas)

## Arquitectura

El sistema soporta **múltiples perfiles de venta**, donde cada uno puede tener credenciales independientes para WhatsApp, Messenger e Instagram.

```
Sistema de Inventario
├── Perfil: Softmobile (bot IA)
│   ├── WhatsApp: +123456789 (phone_number_id, access_token)
│   ├── Messenger: Página Softmobile (page_id, page_access_token)
│   └── Instagram: @softmobile (instagram_account_id, access_token)
│
└── Perfil: TechStore (vendedor humano)
    ├── WhatsApp: +987654321 (phone_number_id, access_token)
    ├── Messenger: Página TechStore (page_id, page_access_token)
    └── Instagram: @techstore (instagram_account_id, access_token)
```

**Clave**: Los webhooks automáticamente routean mensajes entrantes al perfil correcto basado en:
- **WhatsApp**: `phone_number_id` (ID del número de teléfono)
- **Messenger**: `page_id` (ID de la página de Facebook)
- **Instagram**: `instagram_account_id` (ID de la cuenta de Instagram)

## Pasos rápidos

### 1. Crear perfiles en la UI

```
Página: Sales Profiles
+ Nuevo Perfil
├─ Nombre: "Softmobile Bot"
├─ Slug: "softmobile-bot"
├─ Tipo: Bot IA
├─ Canales: ☑ WhatsApp, ☑ Messenger, ☑ Instagram
└─ Guardar
```

### 2. Cargar credenciales de prueba (OPCIONAL - solo para testing)

```bash
cd backend
python3 seed_channel_credentials.py --populate
```

Esto genera credenciales ficticias realistas para cada canal. **Solo para demostración.**

### 3. Obtener credenciales reales de Meta

Ver: [Obtener credenciales de Meta](#obtener-credenciales-de-meta)

### 4. Configurar credenciales en UI

```
Sales Profiles → [Editar Perfil] → Canal Configuration
├─ WhatsApp
│  ├─ Phone Number ID: 123456789
│  └─ Access Token: EAABCD...XYZ
├─ Messenger
│  ├─ Page ID: 987654321
│  └─ Page Access Token: EAABCD...XYZ
└─ Instagram
   ├─ Instagram Account ID: 456789123
   └─ Access Token: EAABCD...XYZ
```

### 5. Validar conexión

```
UI → Sales Profiles → [Estado de integraciones]
Botón "🔌" junto a cada canal
→ Si verde "✓ OK": Credenciales válidas
→ Si rojo "✗ Error": Revisar credenciales/tokens
```

### 6. Publicar backend en HTTPS

Los webhooks de Meta requieren URL pública HTTPS:

```bash
# Opción A: ngrok (rápido, temporal)
ngrok http 8000
# Output: https://xxxx-yyyy-zzzz.ngrok-free.app

# Opción B: Exposé (Laravel/PHP community)
expose share http://localhost:8000

# Opción C: Cloud deployment (Heroku, Railway, etc.)
```

### 7. Registrar webhooks en Meta Developer

Para **cada perfil**, en [Meta Developers → Apps](https://developers.facebook.com):

```
App → Messenger → Settings
├─ Webhook URL: https://yourdomain.com/api/channels/messenger/webhook
├─ Verify Token: (del perfil → configuración)
└─ Subscribe to: messages

App → WhatsApp → Settings
├─ Webhook URL: https://yourdomain.com/api/channels/whatsapp/webhook
├─ Verify Token: (del perfil → configuración)
└─ Subscribe to: messages

App → Instagram → Settings
├─ Webhook URL: https://yourdomain.com/api/channels/instagram/webhook
├─ Verify Token: (del perfil → configuración)
└─ Subscribe to: messages
```

## Obtener credenciales de Meta

### WhatsApp Business API

1. Ir a [Meta Developers](https://developers.facebook.com/)
2. Crear app (Tipo: Business)
3. Producto: WhatsApp → Configuración
4. **Cloud API Access**:
   - Token de acceso permanente (generar)
   - ID de número de teléfono (copiar)
   - ID de número empresarial (copiar)

5. **Verification Token**:
   - En WebHook Settings, crear un token:
   ```
   Verify Token: algo_como_verify_token_123
   ```

**Guardar:**
```
phone_number_id=123456789
access_token=EAA...BCXYZ
verify_token=verify_token_123
```

### Messenger

1. [Meta Developers](https://developers.facebook.com/)
2. App → Messenger → Configuración
3. **Page Access Tokens**:
   - Seleccionar página de Facebook
   - Generar token
   
4. Copiar `page_id` de la página

5. **Verification Token**:
   ```
   Verify Token: messenger_verify_token_456
   ```

**Guardar:**
```
page_id=987654321
page_access_token=EAA...BCXYZ
verify_token=messenger_verify_token_456
```

### Instagram

1. [Meta Developers](https://developers.facebook.com/)
2. App → Instagram → Configuración
3. Conectar conta Instagram a la página Facebook
4. Obtener `instagram_account_id` de la API o Settings
5. **Access Token**: Usar el mismo que Messenger (page_access_token)
6. **Verification Token**:
   ```
   Verify Token: instagram_verify_token_789
   ```

**Guardar:**
```
instagram_account_id=456789123
access_token=EAA...BCXYZ
verify_token=instagram_verify_token_789
```

## Cargar datos de prueba

Para desarrollo/testeo sin credenciales reales:

### Opción 1: Usar script de seed

```bash
cd backend
python3 seed_channel_credentials.py --populate
```

Genera credenciales ficticias pero realistas:
- `phone_number_id`: 15 dígitos
- `page_id`: 18 dígitos
- `access_token`: Token formato Meta (`EAA...`)
- `verify_token`: String único

Ver estado:
```bash
python3 seed_channel_credentials.py
```

Limpiar:
```bash
python3 seed_channel_credentials.py --clear
```

Regenerar nuevos:
```bash
python3 seed_channel_credentials.py --generate
```

## Configurar en la UI

### Crear un nuevo perfil con canales

1. Abrir **Sales Profiles**
2. Click **+ Nuevo Perfil**
3. Completar:
   - **Nombre**: "Softmobile Bot"
   - **Slug**: "softmobile-bot" (único, sin espacios)
   - **Tipo**: Bot IA / Vendedor Humano / Sistema Automático
   - **Canales**: Seleccionar ☑ WhatsApp, ☑ Messenger, ☑ Instagram
4. **Canal Configuration** (Nuevo despues de guardar):
   - Para **WhatsApp**:
     - Phone Number ID: `123456789`
     - Access Token: `EAA...BCXYZ`
     - Verify Token: `whatsapp_verify_123`
   - Para **Messenger**:
     - Page ID: `987654321`
     - Page Access Token: `EAA...BCXYZ`
     - Verify Token: `messenger_verify_456`
   - Para **Instagram**:
     - Instagram Account ID: `456789123`
     - Access Token: `EAA...BCXYZ`
     - Verify Token: `instagram_verify_789`
5. **Guardar**

### Editar credenciales existentes

1. Abrir el perfil
2. Hacer clic **Editar**
3. Sección **Channel Integrations**:
   - Actualizar tokens/IDs
   - Click **Actualizar** (no es automático)

### Ver estado de integraciones

En la tarjeta del perfil, sección "Estado de integraciones":

```
WhatsApp  [✓ Listo]  [🔌]
Messenger [✗ Incompleto] [🔌]
Instagram [✓ Listo]  [🔌]
```

Leyenda:
- **✓ Listo**: Todos los campos requeridos completos
- **✗ Incompleto**: Faltan campos (hover para ver cuáles)
- **🔌 Botón**: Test de conexión (solo si Listo)

### Test de conexión

1. Ir a perfil
2. Junto a cada canal, click botón **🔌**
3. Resultados:
   - **✓ OK** (verde): Token válido, conectado a Meta API
   - **✗ Error** (rojo): Token inválido, expirado o ID incorrecto

El test valida que pueda alcanzar Meta Graph API con las credenciales.

## Registrar webhooks

### Requisitos previos

1. Backend corriendo en HTTPS público (ngrok, Heroku, tu servidor)
2. URL pública: `https://example.com/api/channels/`
3. Credenciales cargadas en perfiles

### Pasos

#### Para WhatsApp

1. [Meta Business Manager](https://business.facebook.com/) → Apps
2. App → WhatsApp → Configuración
3. **Webhook**:
   - Callback URL: `https://example.com/api/channels/whatsapp/webhook`
   - Verify Token: (el que configuraste en el perfil)
   - Subscribe Events: `messages`
   - Click **Verify**

#### Para Messenger

1. [Meta Developers](https://developers.facebook.com/) → App → Messenger
2. **Webhooks**:
   - Callback URL: `https://example.com/api/channels/messenger/webhook`
   - Verify Token: (el que configuraste en el perfil)
   - Subscription Fields: `messages`, `messaging_postbacks`
   - Click **Verify**

#### Para Instagram

1. [Meta Developers](https://developers.facebook.com/) → App → Instagram
2. **Webhooks**:
   - Callback URL: `https://example.com/api/channels/instagram/webhook`
   - Verify Token: (el que configuraste en el perfil)
   - Subscription Fields: `messages`
   - Click **Verify**

### Verificación

Si los webhooks se registran, Meta enviará un GET con `hub.challenge`. El sistema responde automáticamente.

## Pruebas end-to-end

### 1. Prueba local (sin webhook real)

Usa el Swagger UI para simular:

```bash
# Terminal del backend
curl -X POST http://localhost:8000/docs
```

Endpoint: `POST /api/channels/whatsapp/webhook`
Payload:
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "metadata": {"phone_number_id": "123456789"},
        "messages": [{
          "id": "wamid_test_1",
          "from": "34600000000",
          "type": "text",
          "text": {"body": "Hola, ¿cuánto cuesta el iPhone?"}
        }],
        "contacts": [{
          "wa_id": "34600000000",
          "profile": {"name": "Juan"}
        }]
      }
    }]
  }]
}
```

Esperado:
- ✓ Webhook procesado
- ✓ Mensaje enrutado a perfil correcto
- ✓ Respuesta enviada desde perfil (token del perfil)

### 2. Prueba real con Meta webhooks

1. Enviar mensaje real a WhatsApp/Messenger/Instagram del perfil
2. Verificar en logs del backend que llega el webhook
3. Verificar que el bot responde (si está configurado IA)

### 3. Verificar deduplicación

Enviar 2 mensajes idénticos consecutivos:
- El segundo debe ser ignorado (deduplicación en DB)
- Logs deben mostrar `skipped_duplicates: 1`

## Solución de problemas

### Error: "Firma inválida" (HTTP 401)

**Causa**: Verify token incorrecto o no registrado

**Solución**:
1. Verificar que el `verify_token` en el perfil coincida con Meta
2. En Meta → App → Webhook Settings, verificar que sea el correcto
3. Regenerar en ambos lados si es necesario

```bash
# Borrar y regenerar
python3 seed_channel_credentials.py --clear
python3 seed_channel_credentials.py --populate
```

### Error: "Token expirrado" (HTTP 401 en test)

**Causa**: Access token expirado

**Solución**:
1. En Meta → App, regenerar access token
2. Actualizar en UI del perfil
3. Re-test conexión

### Error: "Phone Number ID no encontrado"

**Causa**: ID incorrecto o no registrado en Meta

**Solución**:
1. En Meta → WhatsApp Business, verificar ID exacto
2. Copiar y pegar (no escribir manual)
3. Re-test conexión

### El webhook no llega

**Causa**:
1. URL pública no es HTTPS
2. Webhook no está registrado en Meta
3. Backend down

**Solución**:
1. Verificar HTTPS: `curl https://example.com/api/channels/whatsapp/webhook`
2. En Meta → Webhook Test, enviar test
3. Revisar logs: `docker logs backend`

### El mensaje se procesa pero no se responde

**Causa**: 
1. Bot IA no configurado
2. N8N no conectado
3. Error en lógica de respuesta

**Solución**:
1. Verificar `AIProfileConfig` del perfil
2. Verificar logs: `grep -i "error\|reply" logs/backend.log`
3. Habilitar debug en `.env`: `LOG_LEVEL=DEBUG`

### Estado de integración muestra "Incompleto" pero tienen datos

**Causa**: Campos faltantes todavía

**Solución**:
1. Verificar que NO hay espacios en blanco
2. Verificar que tipo de dato es correcto (número vs string)
3. Editar y guardar nuevamente

Campos requeridos:
- **WhatsApp**: `phone_number_id` + `access_token` (verify_token es opcional pero recomendado)
- **Messenger**: `page_id` + `page_access_token`
- **Instagram**: `instagram_account_id` + `access_token`

## Archivos relacionados

- **Backend**: `backend/app/routers/channel_integrations.py`
- **Models**: `backend/app/models/ai.py` (ProcessedMessage para deduplicación)
- **Frontend**: `src/components/SalesProfilesList.tsx`
- **API Client**: `src/lib/apiClient.ts` → `testChannelConnection()`
- **DB Migration**: `backend/migrate_add_deduplication_table.py`
- **Seed Data**: `backend/seed_channel_credentials.py`

## API Endpoints

### Health Check

```
GET /api/channels/health
→ Muestra estado global + per-perfil de todos los canales
```

### Test Connection

```
POST /api/channels/test-connection/{sales_profile_slug}/{channel}
Ejemplo: POST /api/channels/test-connection/softmobile-bot/whatsapp

Response:
{
  "status": "success" | "error",
  "channel": "whatsapp",
  "sales_profile_slug": "softmobile-bot",
  "details": "Conexión exitosa a Meta Graph API",
  "timestamp": "2024-03-10T15:30:00Z"
}
```

### Webhooks

```
POST /api/channels/whatsapp/webhook
POST /api/channels/messenger/webhook
POST /api/channels/instagram/webhook
```

## Variables de entorno

En `backend/.env`:

```bash
# Meta API (global fallback, si no hay config per-perfil)
META_VERIFY_TOKEN=your_verify_token
WHATSAPP_VERIFY_TOKEN=your_whatsapp_token
MESSENGER_VERIFY_TOKEN=your_messenger_token
INSTAGRAM_VERIFY_TOKEN=your_instagram_token

# Mensaje TTL para deduplicación (segundos)
CHANNEL_MESSAGE_TTL_SECONDS=600

# N8N integration (opcional, si no automanejo)
N8N_WEBHOOK_URL=https://your-n8n.com/webhook/...
```

## Preguntas frecuentes

**P: ¿Puedo usar el mismo token para múltiples perfiles?**
R: Técnicamente sí, pero no es recomendado. Lo ideal es tener credenciales independientes por marca.

**P: ¿Qué pasa si un perfil no tiene credenciales?**
R: Los webhooks no lo encontrarán por cuenta ID, y usarán el perfil global fallback (si está definido).

**P: ¿Cómo manejo diferentes números WhatsApp para diferentes tiendas?**
R: Cada uno es un `phone_number_id` diferente. Meta asigna un ID único por número.

**P: ¿Puedo rotacar tokens sin downtime?**
R: Sí. Actualizar en BD, re-test, luego cambiar en Meta.

**P: ¿Hay límite de perfiles/canales?**
R: No hay límite técnico. La escala depende del servidor.

---

**Última actualización**: March 10, 2026  
**Versión**: 2.0 Multi-Perfil
