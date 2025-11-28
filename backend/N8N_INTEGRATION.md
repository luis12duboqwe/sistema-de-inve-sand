# 🔌 Integraciones con n8n

Esta guía muestra cómo integrar la API de Inventario con n8n para automatizar procesos de ventas.

## 📋 Casos de Uso Comunes

### 1. Chatbot de WhatsApp → Crear Orden

**Flujo:**
1. Cliente envía mensaje por WhatsApp
2. Chatbot identifica productos solicitados
3. n8n crea orden automáticamente
4. Cliente recibe confirmación

**Configuración n8n:**

```
[WhatsApp Trigger] → [Procesar Mensaje] → [HTTP Request] → [Responder Cliente]
```

**Nodo HTTP Request:**
- **Method:** POST
- **URL:** `http://localhost:8000/api/orders`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "profile_slug": "softmobile",
  "canal": "whatsapp",
  "customer_name": "{{ $json.contact_name }}",
  "customer_phone": "{{ $json.phone }}",
  "metodo_pago": "efectivo",
  "items": [
    {
      "product_id": {{ $json.product_id }},
      "cantidad": {{ $json.quantity }}
    }
  ]
}
```

### 2. Consultar Productos Disponibles

**Flujo:**
1. Cliente pregunta por productos
2. Chatbot consulta inventario
3. Responde con productos disponibles

**Nodo HTTP Request:**
- **Method:** GET
- **URL:** `http://localhost:8000/api/products?profile_slug=softmobile&search={{ $json.search_term }}`

**Procesar Respuesta:**
```javascript
// En nodo "Function"
const products = $input.all()[0].json;
const mensaje = products.map(p => 
  `📱 ${p.nombre}\n💰 ${p.moneda} ${p.precio}\n📦 Stock: ${p.stock_disponible}`
).join('\n\n');

return { mensaje };
```

### 3. Verificar Stock Antes de Vender

**Nodo HTTP Request:**
- **Method:** GET
- **URL:** `http://localhost:8000/api/products/{{ $json.product_id }}`

**Validar Stock:**
```javascript
const product = $input.first().json;
const cantidad_solicitada = $('Trigger').item.json.cantidad;

if (product.stock_disponible >= cantidad_solicitada) {
  return { proceder: true, product };
} else {
  return { 
    proceder: false, 
    mensaje: `Lo siento, solo tenemos ${product.stock_disponible} unidades disponibles`
  };
}
```

### 4. Notificación de Stock Bajo

**Flujo Programado:**
```
[Cron] → [Consultar Productos] → [Filtrar Stock Bajo] → [Enviar Notificación]
```

**Consultar Productos:**
- **Method:** GET
- **URL:** `http://localhost:8000/api/products?profile_slug=softmobile`

**Filtrar Stock Bajo:**
```javascript
const products = $input.all()[0].json;
const stockBajo = products.filter(p => p.stock_disponible < 5);

if (stockBajo.length > 0) {
  const mensaje = '⚠️ ALERTA DE STOCK BAJO:\n\n' + 
    stockBajo.map(p => `${p.nombre}: ${p.stock_disponible} unidades`).join('\n');
  
  return { alerta: true, mensaje, productos: stockBajo };
}

return { alerta: false };
```

### 5. Reporte Diario de Ventas

**Flujo:**
```
[Cron Diario] → [Obtener Órdenes] → [Calcular Totales] → [Enviar Reporte]
```

**Obtener Órdenes del Día:**
- **Method:** GET
- **URL:** `http://localhost:8000/api/orders?profile_slug=softmobile`

**Calcular Totales:**
```javascript
const orders = $input.all()[0].json;
const hoy = new Date().toISOString().split('T')[0];

const ordenesHoy = orders.filter(o => 
  o.created_at.startsWith(hoy)
);

const totalVentas = ordenesHoy.reduce((sum, o) => sum + parseFloat(o.total), 0);
const ordenesCompletadas = ordenesHoy.filter(o => o.estado === 'completada').length;

return {
  fecha: hoy,
  total_ordenes: ordenesHoy.length,
  ordenes_completadas: ordenesCompletadas,
  total_ventas: totalVentas,
  mensaje: `📊 Reporte ${hoy}\n💰 ${ordenesHoy.length} órdenes\n💵 HNL ${totalVentas.toFixed(2)}`
};
```

## 🔐 Seguridad (Producción)

Para producción, añade autenticación:

1. Modifica `app/main.py` para incluir API Key:

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "tu-api-key-secreta":
        raise HTTPException(status_code=401, detail="API Key inválida")
    return x_api_key
```

2. En n8n, añade header:
```
X-Api-Key: tu-api-key-secreta
```

## 🌐 Deploy en Producción

### Opción 1: Railway.app
1. Sube el código a GitHub
2. Conecta Railway con tu repo
3. Railway detectará FastAPI automáticamente
4. Actualiza URL en n8n a: `https://tu-app.railway.app`

### Opción 2: Render.com
1. Crea nuevo Web Service
2. Conecta repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Opción 3: VPS (DigitalOcean, etc.)
```bash
# Instalar dependencias del sistema
sudo apt update
sudo apt install python3-pip nginx

# Clonar proyecto
git clone tu-repo
cd backend

# Configurar entorno
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ejecutar con supervisor o systemd
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📊 Ejemplo Completo: Workflow de Venta

```
┌─────────────────┐
│ WhatsApp Trigger│
└────────┬────────┘
         │
    ┌────▼─────────────────┐
    │ Extraer Info Cliente │
    └────┬─────────────────┘
         │
    ┌────▼────────────────┐
    │ Buscar Productos    │ ← GET /api/products?search=...
    └────┬────────────────┘
         │
    ┌────▼────────────────┐
    │ Validar Stock       │
    └────┬────────────────┘
         │
    ┌────▼────────────────┐
    │ Crear Orden         │ ← POST /api/orders
    └────┬────────────────┘
         │
    ┌────▼────────────────┐
    │ Confirmar Cliente   │
    └─────────────────────┘
```

## 💡 Tips

1. **Caché de productos:** En n8n, usa nodo "Cache" para no consultar productos en cada mensaje
2. **Rate limiting:** Implementa límites de peticiones para evitar abusos
3. **Logging:** Activa logs en FastAPI para debug: `uvicorn app.main:app --log-level debug`
4. **Webhooks:** Crea endpoints webhook en FastAPI para notificar a n8n cuando cambia el stock

## 🆘 Troubleshooting

**Error de conexión:**
- Verifica que la API esté corriendo: `curl http://localhost:8000/api/health`
- Si n8n está en Docker, usa `host.docker.internal:8000` en lugar de `localhost:8000`

**Error 422 (Validation Error):**
- Revisa el schema en `/docs`
- Verifica que los tipos de datos coincidan (números como números, no strings)

**Stock insuficiente:**
- La API responde 400 con mensaje descriptivo
- Implementa manejo de errores en n8n para notificar al cliente
