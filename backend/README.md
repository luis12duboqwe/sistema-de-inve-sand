# Sistema de Inventario - Backend API

Backend REST API construido con **FastAPI + SQLAlchemy + SQLite** para gestión de inventario de celulares y accesorios, diseñado para ser consumido por chatbots de ventas.

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
│   ├── database.py          # Configuración SQLAlchemy + SQLite
│   ├── models.py            # Modelos de base de datos (SQLAlchemy)
│   ├── schemas.py           # Schemas de request/response (Pydantic)
│   └── routers/
│       ├── __init__.py
│       ├── profiles.py      # Endpoints de perfiles
│       ├── products.py      # Endpoints de productos
│       └── orders.py        # Endpoints de órdenes (con transacciones)
├── init_db.py               # Script de inicialización
├── requirements.txt         # Dependencias Python
├── inventory.db             # Base de datos SQLite (generada)
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
