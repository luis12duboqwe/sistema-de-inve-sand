# 🚀 Guía Rápida de Inicio - Backend API

## ⚠️ IMPORTANTE
Este backend de FastAPI **NO puede ejecutarse en este entorno Spark**. Debes descargarlo y ejecutarlo localmente en tu máquina.

## 📁 Estructura del Proyecto

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicación principal FastAPI + CORS
│   ├── database.py          # Configuración SQLAlchemy + PostgreSQL
│   ├── models.py            # Modelos de base de datos (SQLAlchemy)
│   ├── schemas.py           # Schemas Pydantic (request/response)
│   └── routers/
│       ├── __init__.py
│       ├── profiles.py      # Endpoints de perfiles
│       ├── products.py      # Endpoints de productos
│       └── orders.py        # Endpoints de órdenes (transacciones)
├── init_db.py                # Script de inicialización
├── requirements.txt          # Dependencias Python
├── start.sh                  # Script inicio Linux/Mac
├── start.bat                 # Script inicio Windows
├── api-examples.json         # Ejemplos de requests
└── README.md                 # Documentación completa
```

## 🏃‍♂️ Inicio Rápido

### Opción 1: Script Automático (Recomendado)

**Linux/Mac:**
```bash
cd backend
chmod +x start.sh
./start.sh
```

**Windows:**
```cmd
cd backend
start.bat
```

### Opción 2: Manual (3 pasos)

```bash
# 1. Crear y activar entorno virtual
python -m venv venv

# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Inicializar base de datos con datos de ejemplo
python init_db.py --with-data

# 4. Ejecutar servidor
uvicorn app.main:app --reload
```

## 🌐 Acceder a la API

- **API Base:** http://localhost:8000
- **Documentación Swagger:** http://localhost:8000/docs ← **¡Úsalo para probar!**
- **Documentación ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/api/health

## 🗄️ Inicializar Datos de Ejemplo

### Con script Python (recomendado):
```bash
python init_db.py --with-data
```

### Con endpoint API:
```bash
curl -X POST http://localhost:8000/api/init-data
```

Esto crea:
- ✅ Perfil "Softmobile" (slug: `softmobile`)
- ✅ 4 productos (2 celulares + 2 accesorios)
- ✅ Stock inicial para cada producto

**Productos creados:**
| ID | Producto | Precio | Stock |
|----|----------|--------|-------|
| 1 | Samsung Galaxy S24 256GB | 18,500 HNL | 5 |
| 2 | iPhone 15 Pro 512GB | 35,000 HNL | 3 |
| 3 | Funda de Silicona | 150 HNL | 50 |
| 4 | Cargador Rápido 20W | 350 HNL | 25 |

## 📡 Endpoints Principales

### Productos
```bash
# Listar todos con stock disponible
GET /api/products

# Filtrar por perfil
GET /api/products?profile_slug=softmobile

# Buscar productos
GET /api/products?search=samsung

# Crear producto
POST /api/products
```

### Órdenes
```bash
# Listar órdenes
GET /api/orders?profile_slug=softmobile

# Crear orden (descuenta stock automáticamente)
POST /api/orders
```

### Perfiles
```bash
# Listar perfiles
GET /api/profiles

# Crear perfil
POST /api/profiles
```

## 📝 Ejemplos de Uso

### Consultar productos disponibles

```bash
curl "http://localhost:8000/api/products?profile_slug=softmobile"
```

### Crear una orden

```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "profile_slug": "softmobile",
    "canal": "whatsapp",
    "customer_name": "Juan Pérez",
    "customer_phone": "+504 1234-5678",
    "metodo_pago": "efectivo",
    "items": [
      {"product_id": 1, "cantidad": 1},
      {"product_id": 3, "cantidad": 2}
    ]
  }'
```

### Ver órdenes creadas

```bash
curl "http://localhost:8000/api/orders?profile_slug=softmobile"
```

## 🔗 Integración con n8n

En n8n, usa el nodo **HTTP Request**:

1. **Method:** POST
2. **URL:** `http://localhost:8000/api/orders`
3. **Body Content Type:** JSON
4. **Body:**
```json
{
  "profile_slug": "{{$json.profile}}",
  "canal": "whatsapp",
  "customer_name": "{{$json.customer_name}}",
  "customer_phone": "{{$json.phone}}",
  "metodo_pago": "efectivo",
  "items": {{$json.items}}
}
```

Ver `N8N_INTEGRATION.md` para más ejemplos.

## ✨ Características Implementadas

✅ **Pydantic Schemas** separados de modelos SQLAlchemy
✅ **Validación automática** de stock antes de crear órdenes
✅ **Transacciones atómicas** (orden + descuento de stock juntos)
✅ **Mensajes de error claros** (perfil no existe, stock insuficiente, etc.)
✅ **Campo stock_disponible** siempre incluido en productos
✅ **CORS habilitado** para cualquier origen
✅ **Documentación automática** en Swagger UI
✅ **Soporte regalos/promociones** (`es_regalo_promocion`)

## 🐛 Solución de Problemas

❌ **Error: "No module named 'app'"**
```bash
# Asegúrate de estar en backend/
cd backend
python init_db.py --with-data
```

❌ **Puerto 8000 ocupado**
```bash
# Usa otro puerto
uvicorn app.main:app --reload --port 8001
```

❌ **Base de datos bloqueada**
```bash
# Detén uvicorn (Ctrl+C) y reinicia
uvicorn app.main:app --reload
```

## 🔍 Testing

### 1. Abre Swagger UI
http://localhost:8000/docs

### 2. Prueba el endpoint `/api/products`
- Click en "GET /api/products"
- Click en "Try it out"
- Añade `softmobile` en `profile_slug`
- Click en "Execute"

### 3. Prueba crear una orden
- Click en "POST /api/orders"
- Click en "Try it out"
- Usa el JSON de ejemplo
- Click en "Execute"

## 📚 Más Información

- **README.md completo:** Detalles técnicos de implementación
- **N8N_INTEGRATION.md:** Ejemplos específicos para n8n
- **api-examples.json:** Colección de ejemplos de requests

## 🎯 Próximos Pasos

1. ✅ Ejecuta `python init_db.py --with-data`
2. ✅ Inicia el servidor con `uvicorn app.main:app --reload`
3. ✅ Abre http://localhost:8000/docs
4. ✅ Prueba crear una orden desde Swagger UI
5. ✅ Verifica que el stock se descontó correctamente
