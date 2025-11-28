# Sistema de Inventario - Backend API

Backend REST API construido con FastAPI + SQLAlchemy + SQLite para gestión de inventario de celulares y accesorios.

## Requisitos

- Python 3.11+
- pip

## Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno (opcional):
```bash
cp .env.example .env
```

## Ejecutar

```bash
uvicorn app.main:app --reload
```

La API estará disponible en: http://localhost:8000

Documentación interactiva: http://localhost:8000/docs

## Inicializar datos de ejemplo

```bash
curl -X POST http://localhost:8000/api/init-data
```

## Endpoints principales

### Productos
- `GET /api/products?profile_slug=softmobile&search=samsung`
- `POST /api/products` - Crear producto

### Órdenes
- `GET /api/orders?profile_slug=softmobile`
- `POST /api/orders` - Crear orden

### Perfiles
- `GET /api/profiles`
- `POST /api/profiles` - Crear perfil

## Estructura del proyecto

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # Aplicación FastAPI principal
│   ├── database.py       # Configuración de base de datos
│   ├── models.py         # Modelos SQLAlchemy
│   ├── schemas.py        # Schemas Pydantic
│   └── routers/
│       ├── __init__.py
│       ├── products.py   # Endpoints de productos
│       ├── orders.py     # Endpoints de órdenes
│       └── profiles.py   # Endpoints de perfiles
├── requirements.txt
└── README.md
```

## Ejemplo de uso desde n8n

### Crear orden:
```json
POST http://localhost:8000/api/orders
Content-Type: application/json

{
  "profile_slug": "softmobile",
  "canal": "whatsapp",
  "customer_name": "Juan Pérez",
  "customer_phone": "+504 1234-5678",
  "metodo_pago": "efectivo",
  "items": [
    {"product_id": 1, "cantidad": 1},
    {"product_id": 2, "cantidad": 2}
  ]
}
```

### Consultar productos:
```
GET http://localhost:8000/api/products?profile_slug=softmobile&search=samsung
```
