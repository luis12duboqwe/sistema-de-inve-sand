# Sistema de Inventario - Backend API

Backend REST API construido con **FastAPI + SQLAlchemy + PostgreSQL** para gestión de inventario de celulares y accesorios, diseñado para ser consumido por chatbots de ventas.

## 🎯 Características Principales

- ✅ **Pydantic Schemas**: Separación clara entre modelos de BD (SQLAlchemy) y esquemas de API (Pydantic)
- ✅ **Validación robusta**: Manejo de errores con mensajes claros y específicos
- ✅ **Transacciones atómicas**: Creación de órdenes y descuento de stock en una sola transacción
- ✅ **CORS habilitado**: Configurado para permitir llamadas desde cualquier origen
- ✅ **Documentación automática**: Swagger UI disponible en `/docs`
- ✅ **Stock en tiempo real**: Cálculo automático de `stock_disponible` en todas las consultas

## 📋 Requisitos

- Python 3.11+
- pip

## 🚀 Instalación

### 1. Crear entorno virtual

```bash
cd backend
python -m venv venv

# En Linux/Mac:
source venv/bin/activate

# En Windows:
venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Inicializar base de datos

Opción A - Con script Python (recomendado):
```bash
python init_db.py --with-data
```

Opción B - Con endpoint API:
```bash
# Primero inicia el servidor (en otra terminal)
uvicorn app.main:app --reload

# Luego ejecuta:
curl -X POST http://localhost:8000/api/init-data
```

## 🏃 Ejecutar el servidor

```bash
uvicorn app.main:app --reload
```

El servidor estará disponible en:
- **API**: http://localhost:8000
- **Documentación interactiva**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📚 Endpoints principales

## 🔐 Autenticación para Integraciones IA (n8n / bots)

Los endpoints de IA conversacional ahora requieren autenticación por una de estas vías:

- JWT de usuario activo (flujo normal del frontend)
- Token de servicio para integraciones (n8n/bots)

Endpoints protegidos por integración:

- `POST /api/ai/context`
- `POST /api/ai/reply`
- `POST /api/ai/log`
- `POST /api/ai/training/submit`
- `POST /api/ai/flag-troll`
- `POST /api/ai/create-order`
- `POST /api/ai/handle-message`

Configura `N8N_AUTH_TOKEN` en `.env` y envíalo en alguno de estos headers:

- `X-N8N-Token: <token>`
- `X-AI-Service-Token: <token>`
- `Authorization: Bearer <token>`

Ejemplo:

```bash
curl -X POST "http://localhost:8000/api/ai/context" \
  -H "Content-Type: application/json" \
  -H "X-N8N-Token: tu-token-secreto" \
  -d '{
    "sales_profile_slug": "bot-principal",
    "customer_phone": "50499990000",
    "customer_name": "Cliente Demo",
    "message_content": "Hola, que teléfonos tienen?"
  }'
```

Crear orden en una sola llamada desde n8n/bot:

```bash
curl -X POST "http://localhost:8000/api/ai/create-order" \
  -H "Content-Type: application/json" \
  -H "X-N8N-Token: tu-token-secreto" \
  -d '{
    "sales_profile_slug": "bot-principal",
    "source_location_id": 1,
    "customer_phone": "50499990000",
    "customer_name": "Cliente Demo",
    "canal": "whatsapp",
    "metodo_pago": "efectivo",
    "items": [
      {
        "product_query": "iPhone 13",
        "cantidad": 1
      }
    ],
    "auto_link_interaction": true
  }'
```

Nota: para productos serializados debes enviar `imeis` en cada item.

Flujo completo sin n8n (responder + log + crear orden opcional):

```bash
curl -X POST "http://localhost:8000/api/ai/handle-message" \
  -H "Content-Type: application/json" \
  -H "X-N8N-Token: tu-token-secreto" \
  -d '{
    "sales_profile_slug": "bot-principal",
    "customer_phone": "50499990000",
    "customer_name": "Cliente Demo",
    "message_content": "Listo, confirmo la compra",
    "order_intent": {
      "source_location_id": 1,
      "canal": "whatsapp",
      "metodo_pago": "efectivo",
      "items": [
        { "product_query": "iPhone 13", "cantidad": 1 }
      ],
      "auto_create": true,
      "auto_link_interaction": true
    }
  }'
```

### Webhooks automáticos de canales (sin n8n)

Si quieres copiar/pegar rápido, usa esta plantilla:

- `backend/.env.example.channels`

Valida tu configuración antes de conectar Meta:

```bash
cd backend
python check_channels_config.py
```

También puedes consultar el estado desde la API:

```bash
GET /api/channels/health
```

Puedes conectar Meta directamente y el sistema responderá automáticamente cada mensaje entrante:

- `GET /api/channels/whatsapp/webhook` (verificación)
- `POST /api/channels/whatsapp/webhook` (mensajes entrantes)
- `GET /api/channels/messenger/webhook` (verificación)
- `POST /api/channels/messenger/webhook` (mensajes entrantes)
- `GET /api/channels/instagram/webhook` (verificación)
- `POST /api/channels/instagram/webhook` (mensajes entrantes)

Variables mínimas recomendadas en `.env`:

```env
# Verificación webhook (puedes usar uno global o uno por canal)
META_VERIFY_TOKEN=tu_verify_token_global
WHATSAPP_VERIFY_TOKEN=
MESSENGER_VERIFY_TOKEN=
INSTAGRAM_VERIFY_TOKEN=

# Seguridad opcional (si se configura, valida X-Hub-Signature-256)
META_APP_SECRET=tu_meta_app_secret

# Credenciales de envío
WHATSAPP_ACCESS_TOKEN=EAAG...
WHATSAPP_PHONE_NUMBER_ID=1234567890
META_PAGE_ACCESS_TOKEN=EAAG...

# Perfil IA por defecto para responder mensajes
CHANNEL_DEFAULT_SALES_PROFILE_SLUG=bot-principal
# Opcional por canal
WHATSAPP_DEFAULT_SALES_PROFILE_SLUG=
MESSENGER_DEFAULT_SALES_PROFILE_SLUG=
INSTAGRAM_DEFAULT_SALES_PROFILE_SLUG=

# Ventana de deduplicación de mensajes
CHANNEL_MESSAGE_TTL_SECONDS=600
```

Notas:

- Si hay `META_APP_SECRET`, el webhook exige firma válida.
- WhatsApp usa `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_PHONE_NUMBER_ID` para responder.
- Messenger/Instagram usan `META_PAGE_ACCESS_TOKEN` para responder.

#### Modo multi-perfil (recomendado para múltiples marcas/tiendas)

Para manejar varias marcas (ej: `softmobile`, `techstore`, etc.) en un solo backend, configura cada
`SalesProfile.configuracion` con sus credenciales e identificadores de canal.

Estructura esperada en `configuracion`:

```json
{
  "channel_integrations": {
    "whatsapp": {
      "phone_number_id": "1234567890",
      "access_token": "EAAG...",
      "verify_token": "verify-softmobile-wa"
    },
    "messenger": {
      "page_id": "987654321",
      "page_access_token": "EAAG...",
      "verify_token": "verify-softmobile-mg"
    },
    "instagram": {
      "instagram_account_id": "1122334455",
      "page_access_token": "EAAG...",
      "verify_token": "verify-softmobile-ig"
    }
  }
}
```

Comportamiento:

- El webhook detecta `phone_number_id/page_id/instagram_account_id` entrante y enruta al `sales_profile_slug` correcto.
- La respuesta saliente usa los tokens del perfil correspondiente.
- Si no encuentra match por perfil, usa fallback global por variables de entorno.

### Perfiles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/profiles` | Lista todos los perfiles activos |
| POST | `/api/profiles` | Crea un nuevo perfil |
| GET | `/api/profiles/{id}` | Obtiene un perfil por ID |

### Productos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/products` | Lista productos con stock disponible |
| POST | `/api/products` | Crea un nuevo producto |
| GET | `/api/products/{id}` | Obtiene un producto por ID |

**Parámetros de consulta para GET /api/products:**
- `profile_slug` (opcional): Filtra por perfil (ej: `softmobile`)
- `search` (opcional): Busca en nombre, marca y modelo

**Ejemplo:**
```bash
GET /api/products?profile_slug=softmobile&search=samsung
```

### Órdenes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/orders` | Lista todas las órdenes |
| POST | `/api/orders` | Crea una nueva orden |
| GET | `/api/orders/{id}` | Obtiene una orden por ID |

**Parámetros de consulta para GET /api/orders:**
- `profile_slug` (opcional): Filtra por perfil

## 🔧 Detalles de implementación

### 1. Schemas vs Models

- **Models** (`models.py`): Modelos SQLAlchemy para la base de datos
- **Schemas** (`schemas.py`): Schemas Pydantic para request/response

```python
# ✅ CORRECTO: Usar schemas en endpoints
@router.post("", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    ...
```

### 2. Manejo de errores

#### Error 404 - Perfil no encontrado
```json
{
  "detail": "El perfil con slug 'softmobile' no fue encontrado"
}
```

#### Error 400 - Stock insuficiente
```json
{
  "detail": "Stock insuficiente para 'iPhone 15 Pro' (ID: 2). Disponible: 3, Solicitado: 5"
}
```

### 3. Transacciones atómicas

La creación de órdenes garantiza consistencia mediante transacciones:

```python
try:
    # 1. Validar stock
    # 2. Crear orden
    # 3. Crear order items
    # 4. Descontar stock
    db.commit()  # Todo o nada
except Exception:
    db.rollback()  # Si algo falla, se revierte todo
    raise
```

### 4. Campo stock_disponible

**Siempre incluido** en respuestas de productos, calculado desde la tabla `stock`:

```json
{
  "id": 1,
  "nombre": "Samsung Galaxy S24",
  "precio": 18500.00,
  "stock_disponible": 5  // ← Siempre presente
}
```

### 5. CORS

Configurado para desarrollo. **Importante**: Restringir en producción:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📝 Ejemplos de uso

### Crear un perfil

```bash
curl -X POST "http://localhost:8000/api/profiles" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mi Tienda",
    "slug": "mi-tienda",
    "active": true
  }'
```

### Consultar productos

```bash
curl "http://localhost:8000/api/products?profile_slug=softmobile&search=samsung"
```

### Crear una orden

```bash
curl -X POST "http://localhost:8000/api/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_slug": "softmobile",
    "canal": "whatsapp",
    "customer_name": "Juan Pérez",
    "customer_phone": "+504 1234-5678",
    "metodo_pago": "efectivo",
    "items": [
      {
        "product_id": 1,
        "cantidad": 1,
        "es_regalo_promocion": false
      },
      {
        "product_id": 3,
        "cantidad": 2,
        "es_regalo_promocion": false
      }
    ]
  }'
```

### Respuesta exitosa

```json
{
  "id": 1,
  "profile_id": 1,
  "customer_name": "Juan Pérez",
  "customer_phone": "+504 1234-5678",
  "canal": "whatsapp",
  "metodo_pago": "efectivo",
  "total": 18800.00,
  "estado": "pendiente",
  "created_at": "2024-01-15T10:30:00",
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "cantidad": 1,
      "precio_unitario": 18500.00,
      "es_regalo_promocion": false,
      "product": {
        "id": 1,
        "nombre": "Samsung Galaxy S24 256GB Negro",
        "stock_disponible": 4
      }
    }
  ]
}
```

## 🏗️ Estructura del proyecto

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicación FastAPI principal + CORS
│   ├── database.py          # Configuración SQLAlchemy + PostgreSQL
│   ├── models.py            # Modelos de base de datos (SQLAlchemy)
│   ├── schemas.py           # Schemas de request/response (Pydantic)
│   └── routers/
│       ├── __init__.py
│       ├── profiles.py      # Endpoints de perfiles
│       ├── products.py      # Endpoints de productos
│       └── orders.py        # Endpoints de órdenes (con transacciones)
├── init_db.py               # Script de inicialización
├── requirements.txt         # Dependencias Python
├── docker-compose.yml       # PostgreSQL local para desarrollo
└── README.md
```

## 🔍 Testing con n8n

### Webhook de nueva orden

```javascript
// n8n HTTP Request node
{
  "method": "POST",
  "url": "http://localhost:8000/api/orders",
  "body": {
    "profile_slug": "{{ $json.profile }}",
    "canal": "whatsapp",
    "customer_name": "{{ $json.customer_name }}",
    "customer_phone": "{{ $json.phone }}",
    "metodo_pago": "efectivo",
    "items": {{ $json.items }}
  }
}
```

### Consulta de productos

```javascript
// n8n HTTP Request node
{
  "method": "GET",
  "url": "http://localhost:8000/api/products",
  "qs": {
    "profile_slug": "softmobile",
    "search": "{{ $json.search_term }}"
  }
}
```

## 🐛 Troubleshooting

### Error: "No module named 'app'"

```bash
# Asegúrate de estar en el directorio backend/
cd backend
python init_db.py --with-data
```

### Error: "database is locked"

```bash
# Detén el servidor uvicorn y vuelve a intentar
# O usa un SessionLocal nuevo para cada operación
```

### Stock negativo después de orden

```bash
# Esto NO debería ocurrir. Si pasa:
# 1. Verifica que las transacciones estén funcionando
# 2. Revisa los logs para ver si hubo rollback
# 3. La validación debe prevenir esto
```

## 📖 Documentación adicional

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- Ver `N8N_INTEGRATION.md` para ejemplos de integración con n8n
- Ver `QUICKSTART.md` para guía rápida de inicio

## 🛡️ Seguridad

Para producción:

1. **Cambiar CORS** a dominios específicos
2. **Agregar autenticación** (OAuth2, JWT)
3. **Variables de entorno** para configuración sensible
4. **Rate limiting** para prevenir abuso
5. **HTTPS** obligatorio

## 📄 Licencia

Ver archivo LICENSE en el directorio raíz del proyecto.
