# 🚀 Guía Rápida de Inicio - Backend API

## ⚠️ IMPORTANTE
Este backend de FastAPI **NO puede ejecutarse en este entorno Spark**. Debes descargarlo y ejecutarlo localmente en tu máquina.

## 📁 Estructura del Proyecto

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicación principal FastAPI
│   ├── database.py          # Configuración SQLAlchemy
│   ├── models.py            # Modelos de base de datos
│   ├── schemas.py           # Schemas Pydantic (validación)
│   └── routers/
│       ├── __init__.py
│       ├── profiles.py      # Endpoints de perfiles
│       ├── products.py      # Endpoints de productos
│       └── orders.py        # Endpoints de órdenes
├── requirements.txt         # Dependencias Python
├── start.sh                 # Script inicio Linux/Mac
├── start.bat               # Script inicio Windows
├── api-examples.json       # Ejemplos de requests
└── README.md               # Documentación completa
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

### Opción 2: Manual

```bash
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar entorno virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar servidor
uvicorn app.main:app --reload
```

## 🌐 Acceder a la API

- **API Base:** http://localhost:8000
- **Documentación Interactiva:** http://localhost:8000/docs
- **Documentación Alternativa:** http://localhost:8000/redoc

## 🔧 Inicializar Datos de Ejemplo

```bash
curl -X POST http://localhost:8000/api/init-data
```

Esto creará:
- ✅ Perfil "Softmobile"
- ✅ 4 productos (2 celulares + 2 accesorios)
- ✅ Stock inicial para cada producto

## 📡 Endpoints Principales

### Productos
```bash
# Listar todos los productos con stock
GET http://localhost:8000/api/products

# Filtrar por perfil
GET http://localhost:8000/api/products?profile_slug=softmobile

# Buscar productos
GET http://localhost:8000/api/products?search=samsung

# Crear producto
POST http://localhost:8000/api/products
```

### Órdenes
```bash
# Listar órdenes
GET http://localhost:8000/api/orders

# Crear orden
POST http://localhost:8000/api/orders
```

### Perfiles
```bash
# Listar perfiles
GET http://localhost:8000/api/profiles

# Crear perfil
POST http://localhost:8000/api/profiles
```

## 📝 Ejemplo de Crear Orden (desde n8n o curl)

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

## ✨ Características Implementadas

✅ **Validación automática** de datos con Pydantic
✅ **Verificación de stock** antes de crear órdenes
✅ **Descuento automático** de inventario al crear órdenes
✅ **Soporte para regalos/promociones** (es_regalo_promocion)
✅ **Filtrado y búsqueda** de productos
✅ **CORS habilitado** para consumo desde cualquier origen
✅ **Documentación interactiva** auto-generada
✅ **Manejo de errores** con mensajes descriptivos

## 🗄️ Base de Datos

El archivo SQLite `inventory.db` se crea automáticamente al ejecutar el servidor por primera vez.

## 🧪 Probar la API

Abre http://localhost:8000/docs en tu navegador para acceder a la interfaz Swagger UI donde puedes:
- Ver todos los endpoints
- Probar cada endpoint directamente
- Ver los schemas de datos
- Ver respuestas de ejemplo

## 📞 Soporte

Ver `README.md` para más detalles y `api-examples.json` para ejemplos de todas las peticiones.
