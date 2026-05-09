# Sistema de Solicitudes de Fotos con Handoff Transparente

## Problema que resuelve

Cuando un cliente le pide fotos al bot (ej: "Quiero ver el iPhone 15 en gris"), el bot **no tiene fotos almacenadas**. 

**Solución**: El bot dice al cliente "dame un momento" y por detrás pide a un agente humano encargado que envíe las fotos. El cliente **nunca se da cuenta** de que fue un humano, cree que el bot fue quien tomó las fotos.

---

## Flujo completo

```
1. CLIENTE                    2. BOT                3. AGENTE
┌──────────────┐            ┌──────────────┐       ┌──────────────┐
│ "Quiero ver  │            │              │       │              │
│ fotos iPhone │─────────►  │ Detecta que  │       │              │
│ 15 gris"     │            │ pide fotos   │       │              │
└──────────────┘            └──────────────┘       └──────────────┘
                                   │
       ┌───────────────────────────┼───────────────────────────┐
       │                           │                           │
       ▼                           ▼                           ▼
┌──────────────┐            ┌──────────────┐       ┌──────────────┐
│ "Dame un     │            │ POST         │       │ Ve dashboard │
│ momento..."  │            │ /photo-reqs  │──────►│ "Juan pide   │
│              │            │ /create      │       │ fotos gris"  │
└──────────────┘            └──────────────┘       └──────────────┘
                                                           │
                                                           ▼
                                                    Toma/carga fotos
                                                    (teléfono, galería)
                                                           │
                                                           ▼
                                                    POST /photo-requests
                                                    /{id}/media
                                                           │
       ┌───────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────┐
  │ WhatsApp    │
  │ Messenger   │
  │ Instagram   │
  │             │
  │ Fotos       │
  │ enviadas    │
  │ al cliente  │
  └─────────────┘
       │
       ▼
┌──────────────┐
│ Cliente      │
│ recibe fotos │
│ (cree que    │
│ del bot)     │
└──────────────┘
```

---

## Componentes del sistema

### 1. **Modelos de BD** (`backend/app/models/photos.py`)

```python
PhotoRequest {
  id,
  customer_id,           # Teléfono del cliente
  product_id,            # ID del producto
  product_name,          # "iPhone 15 Pro"
  color_requested,       # "gris"
  size_requested,        # "128GB"
  status,                # pending, in_progress, completed, failed
  assigned_to_user_id,   # Agente encargado
  photo_urls,            # ["https://...", "https://..."]
  created_at, resolved_at
}

PhotoRequestMediaItem {
  id,
  photo_request_id,
  media_url,            # URL de la foto (S3, Cloudinary)
  media_type,           # "photo", "video", "360_view"
  uploaded_by_user_id,  # Quién la cargó
  sent_to_customer_at,  # Cuándo se envió
  customer_viewed_at    # Cuándo el cliente la vio
}
```

### 2. **Detección de solicitud** (`backend/app/utils/photo_detection.py`)

La función `detect_photo_request(text)` reconoce patrones como:
- "foto", "fotos", "imagen", "imagenes"
- "muéstrame", "déjame ver", "cómo se ve"
- "en qué colores", "variantes de color"
- "photo", "picture", "show me", "let me see"

```python
from app.utils.photo_detection import detect_photo_request, extract_photo_request_context

detected = detect_photo_request("Quiero ver fotos del iPhone 15 en gris")
# True

color, size = extract_photo_request_context("Quiero ver fotos del iPhone 15 en gris")
# ("gris", None)
```

### 3. **Routers de API** (`backend/app/routers/photo_requests.py`)

#### **Crear solicitud** (llamado por el bot)
```http
POST /api/photo-requests/create
Content-Type: application/json

{
  "customer_id": "34600000000",
  "product_id": 5,
  "product_name": "iPhone 15 Pro",
  "color_requested": "gris",
  "size_requested": null,
  "additional_notes": null
}

Query params (opcional):
  ?sales_profile_slug=softmobile-bot
  &channel=whatsapp
  &customer_name=Juan
```

**Respuesta**:
```json
{
  "id": 42,
  "customer_id": "34600000000",
  "product_name": "iPhone 15 Pro",
  "color_requested": "gris",
  "status": "pending",
  "created_at": "2024-03-10T15:30:00Z"
}
```

#### **Listar solicitudes pendientes** (para dashboard del agente)
```http
GET /api/photo-requests/pending
  ?assigned_to_me=true
  &status=pending
```

**Respuesta**:
```json
[
  {
    "id": 42,
    "customer_id": "34600000000",
    "product_name": "iPhone 15 Pro",
    "color_requested": "gris",
    "status": "pending",
    "assigned_to_user_id": 7,
    "media_items": [],
    "created_at": "2024-03-10T15:30:00Z"
  }
]
```

#### **Cargar foto/video** (agente)
```http
POST /api/photo-requests/42/media
Content-Type: application/json

{
  "media_url": "https://cdn.example.com/iphone15_gris_1.jpg",
  "media_type": "photo",
  "metadata": {
    "camera_angle": "frontal",
    "lighting": "natural"
  }
}
```

#### **Enviar fotos al cliente** (agente presiona botón)
```http
POST /api/photo-requests/42/send-to-customer
```

**Qué hace**:
1. Obtiene todas las fotos no enviadas de la solicitud
2. Detecta el canal original (WhatsApp / Messenger / Instagram)
3. Envía las fotos al cliente por ese canal
4. Marca fotos como `sent_to_customer_at`
5. Marca solicitud como `status=completed`
6. El cliente recibe las fotos (cree que del bot)

---

## Integración en el Bot IA

### Instrucción para el prompt GPT-4

El prompt del bot debe incluir:

```
## Solicitud de Fotos

Si el cliente pide fotos de un producto (ej: "Quiero ver imagenes", "Muéstrame en gris"):

1. Responde al cliente: "Dame un momento, estoy tomando fotos..."
2. Internamente, llama: POST /api/photo-requests/create
3. El agente encargado recibirá una notificación
4. Las fotos se enviarán automáticamente quando el agente las cargue
5. Luego continúa la conversación normalmente

Ejemplo:
- Cliente: "Fotos del iPhone 15 en gris"
- Tu respuesta: "Claro, dame un segundo que busco las imágenes"
- (creas request) → (notificas agente internamente)
- (esperas) → (agente te envía foto por API)
- (recibes foto en context) → (la envías al cliente)
- Tu: "Aquí están las fotos. Como ves, el color gris..."
```

### Código en `routers/ai_intelligence.py`

En `handle_message_without_n8n()`:

```python
from app.utils.photo_detection import detect_photo_request, extract_photo_request_context
from app.schemas.photos import PhotoRequestCreate

async def handle_message_without_n8n(...):
    # ... procesamiento normal ...
    
    # DETECTAR si cliente pide fotos
    if detect_photo_request(customer_message):
        color, size = extract_photo_request_context(customer_message)
        
        # Obtener producto mencionado (podría mejorar matching aquí)
        product_name = extract_product_name_from_message(customer_message)
        
        attempt create_photo_request = PhotoRequestCreate(
            customer_id=customer_phone,
            product_name=product_name,
            color_requested=color,
            size_requested=size
        )
        
        # Crear request en BD (pero NO bloquea la respuesta)
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/photo-requests/create",
                json=attempt_create_photo_request.dict(),
                params={
                    "sales_profile_slug": sales_profile.slug,
                    "channel": channel,
                    "customer_name": customer_name
                }
            )
            request_id = response.json().get("id")
            logger.info(f"Photo request created: {request_id}")
        except Exception as e:
            logger.error(f"Error creating photo request: {e}")
        
        # Respuesta al cliente
        bot_response = "Dame un momento, estoy tomando fotos de los colores disponibles..."
    
    else:
        # Respuesta normal sin fotos
        bot_response = (resultado del GPT-4)
    
    # ... enviar respuesta ...
```

---

## Dashboard del Agente

### UI Component: `PhotoRequestsDashboard.tsx`

```tsx
import { PhotoRequestsDashboard } from '@/components/PhotoRequestsDashboard'

// En admin panel o dashboard:
<PhotoRequestsDashboard />
```

**Funcionalidades**:
1. Lista solicitudes pendientes: "Cliente X pide fotos iPhone 15 gris"
2. Botón para cargar foto: Ingresa URL de imagen
3. Previsualización de fotos cargadas
4. Botón "Enviar fotos al cliente" → POST /send-to-customer
5. Botón "Rechazar" → Marca status=failed

**Vista**:
```
📸 Solicitudes de Fotos Pendientes

┌─────────────────────────────────────┐
│ iPhone 15 Pro                       │
│ Cliente: 34600000000                │
│ Color: gris • Solicitado hace: 5 min│
│                               [PENDIENTE]
└─────────────────────────────────────┘

Al hacer click:
┌─────────────────────────────────────┐
│ 📸 iPhone 15 Pro                   │
│ Solicitud de 34600000000            │
├─────────────────────────────────────┤
│ Color: gris                         │
│ Tamaño: No especificó               │
│                                     │
│ Fotos cargadas (0)                  │
│ [URL: _________]  [+ Cargar]        │
│                                     │
│ [Enviar fotos al cliente] [Rechazar]│
└─────────────────────────────────────┘
```

---

## Flujo de datos

### 1. Cliente pide fotos

```
WhatsApp: "Quiero fotos del iPhone 15 en gris"
    ↓
Webhook /channels/whatsapp/webhook
    ↓
Bot recibe mensaje
    ↓
detect_photo_request("Quiero fotos...") → True
    ↓
extract_photo_request_context() → ("gris", None)
```

### 2. Bot crea solicitud

```
POST /api/photo-requests/create
{
  "customer_id": "34600000000",
  "product_name": "iPhone 15 Pro",
  "color_requested": "gris"
}
    ↓
Backend: Crea PhotoRequest en BD
    ↓
Backend: Notifica al agente (email, SMS, WhatsApp interno)
    ↓
Response: {"id": 42, ...}
```

### 3. Bot responde al cliente

```
[Bot → Cliente]
"Dame un momento, estoy tomando fotos de los colores disponibles..."

(Cliente ve respuesta, cree que el bot está tomando fotos)
```

### 4. Agente ve solicitud

```
Dashboard /photo-requests/pending
    ↓
Agente ve: "Juan (34600000000) pide fotos iPhone 15 gris"
    ↓
Agente hace click → Dialog abierto
```

### 5. Agente carga foto

```
Input: https://cdn.example.com/iphone15_gris.jpg
Click: [+ Cargar]
    ↓
POST /api/photo-requests/42/media
{
  "media_url": "https://cdn.example.com/iphone15_gris.jpg",
  "media_type": "photo"
}
    ↓
Backend: Agrega PhotoRequestMediaItem
    ↓
PhotoRequest.status: pending → in_progress
```

### 6. Agente envía fotos

```
Click: [Enviar fotos al cliente]
    ↓
POST /api/photo-requests/42/send-to-customer
    ↓
Backend:
  1. Obtiene todas las fotos no enviadas
  2. Detecta channel original (whatsapp)
  3. Envía WhatsApp al cliente: [FOTO] + mensaje
  4. Marca sent_to_customer_at
  5. Marca status=completed
```

### 7. Cliente recibe fotos

```
WhatsApp: [Foto] + "Aquí están las fotos del iPhone 15..."

Cliente: "¡Qué rápido! El bot es muy eficiente"
(Sin saber que fue un agente humano)
```

---

## Permisos RBAC requeridos

Agregar a sistema de permisos:

```python
PERMISSIONS = {
    "photo_requests:list": "Ver solicitudes de fotos",
    "photo_requests:read": "Ver detalles de solicitud",
    "photo_requests:update": "Actualizar estado de solicitud",
    "photo_requests:upload": "Cargar fotos/videos",
    "photo_requests:send": "Enviar fotos al cliente",
}

ROLES = {
    "photo_handler": [
        "photo_requests:list",
        "photo_requests:read",
        "photo_requests:update",
        "photo_requests:upload",
        "photo_requests:send"
    ]
}
```

---

## Variables de entorno

Agregar a `.env`:

```bash
# Agente encargado de fotos (fallback)
PHOTO_REQUEST_DEFAULT_HANDLER_USER_ID=1

# Cola de notificaciones (opcional)
PHOTO_REQUEST_NOTIFY_VIA=email,sms,whatsapp
PHOTO_REQUEST_NOTIFY_PHONE=+34600000000

# Almacenamiento de fotos (S3, Cloudinary, etc)
MEDIA_STORAGE_PROVIDER=s3  # o cloudinary, local
MEDIA_S3_BUCKET=fotos-productos
```

---

## Consideraciones de UX

1. **Bot responde INMEDIATAMENTE** ("dame un momento...")
2. **No bloquea** si agente está offline (fotos se envían cuando agente cargue)
3. **Transparente**: Cliente nunca se da cuenta que fue humano
4. **Smart fallback**: Si agente no responde en X minutos, bot puede "disculparse" o escalar
5. **Tracking**: Client puede ver si fotos fueron vistas

---

## TODO / Mejoras futuras

- [x] Notificación por email al agente cuando SMTP está configurado
- [x] Upload local/S3 para fotos y videos
- [x] Envío al cliente por WhatsApp/Messenger/Instagram/Facebook con credenciales reales
- [ ] Notificación adicional por SMS/WhatsApp al agente
- [ ] Soporte para cargar múltiples fotos a la vez desde el dashboard
- [ ] Galería interactiva (360°, video enriquecido)
- [ ] Auto-tagging de fotos (por color, ángulo, etc.)
- [ ] Timeout: Si agente no responde en X min, crear "respuesta de espera"
- [ ] Analytics: Ver cuánto tarda agente, satisfacción del cliente
- [ ] A/B testing: ¿Es mejor directo agente o bot con handoff?

---

**Versión**: 1.1  
**Última actualización**: May 4, 2026
