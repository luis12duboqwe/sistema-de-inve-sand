# Sistema de Inventario - Integración Frontend + Backend

Este proyecto conecta el frontend React con el backend FastAPI para gestión completa de inventario.

## 🎯 Arquitectura

El sistema soporta **dos modos de operación**:

### 1. Modo Local (por defecto)
- Datos almacenados en **Spark KV** (almacenamiento local del navegador)
- No requiere backend
- Ideal para desarrollo y pruebas rápidas
- Datos persisten entre sesiones

### 2. Modo API
- Conectado al **backend FastAPI**
- Base de datos SQLite compartida
- Ideal para producción y múltiples usuarios
- Soporte completo de transacciones atómicas

## 🚀 Inicio Rápido

### Opción A: Solo Frontend (Modo Local)

```bash
# Instalar dependencias
npm install

# Iniciar el servidor de desarrollo
npm run dev
```

La aplicación estará disponible en http://localhost:5173

### Opción B: Frontend + Backend (Modo API)

#### 1. Iniciar el Backend

```bash
# En el directorio backend/
cd backend
python -m venv venv

# Activar entorno virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Inicializar base de datos con datos de prueba
python init_db.py --with-data

# Iniciar servidor FastAPI
uvicorn app.main:app --reload
```

El backend estará disponible en http://localhost:8000

#### 2. Iniciar el Frontend

```bash
# En el directorio raíz
npm install
npm run dev
```

#### 3. Configurar Conexión

1. Abre la aplicación en http://localhost:5173
2. Haz clic en el icono de **engranaje (⚙️)** en la esquina superior derecha
3. Activa el switch **"Usar Backend API"**
4. Verifica que la URL sea `http://localhost:8000/api`
5. Haz clic en **"Probar Conexión"** para verificar
6. Si aparece ✓, haz clic en **"Guardar"**
7. **Recarga la página** para aplicar los cambios

#### 4. (Opcional) Cargar Datos de Prueba

En el diálogo de configuración, haz clic en **"Cargar Datos de Prueba"** para inicializar el backend con:
- Perfil "Softmobile"
- 4 productos de ejemplo (2 celulares, 2 accesorios)
- Stock inicial para cada producto

## 📁 Estructura del Proyecto

```
/
├── src/
│   ├── components/
│   │   ├── SettingsDialog.tsx         # Configuración de backend
│   │   ├── NewOrderDialog.tsx
│   │   ├── NewProductDialog.tsx
│   │   └── ...
│   ├── lib/
│   │   ├── apiClient.ts               # Cliente HTTP para FastAPI
│   │   ├── inventoryService.ts        # Servicio local (Spark KV)
│   │   ├── inventoryServiceFactory.ts # Factory que elige backend
│   │   └── types.ts
│   └── App.tsx
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app
│   │   ├── models.py                  # Modelos SQLAlchemy
│   │   ├── schemas.py                 # Schemas Pydantic
│   │   └── routers/
│   │       ├── profiles.py
│   │       ├── products.py
│   │       └── orders.py
│   ├── init_db.py
│   └── requirements.txt
│
├── PRD.md
└── README.md
```

## 🔧 Configuración

### Variables de Configuración

La configuración se guarda automáticamente en **Spark KV**:

- `settings_use_api` (boolean): Si está activado el modo API
- `settings_api_url` (string): URL del backend (por defecto: `http://localhost:8000/api`)

### Cambiar Backend en Tiempo de Ejecución

1. Abre el diálogo de configuración (⚙️)
2. Cambia el modo
3. Guarda los cambios
4. **Recarga la página**

## 🔄 Migración de Datos

### De Local a API

1. Exporta los datos manualmente (si necesario)
2. Usa el endpoint `/api/init-data` o crea datos nuevos desde la UI
3. Cambia a modo API en configuración

### De API a Local

1. Cambia a modo local en configuración
2. Los datos del API permanecen intactos
3. Los datos locales son independientes

## 🧪 Testing

### Probar Conexión API

El diálogo de configuración incluye un botón **"Probar Conexión"** que:
1. Hace ping al endpoint `/api/health`
2. Muestra ✓ si conecta exitosamente
3. Muestra ✗ si hay error de conexión

### Endpoints Disponibles

Ver documentación completa en:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📚 Documentación Adicional

- **Backend**: Ver `backend/README.md` para detalles del API
- **PRD**: Ver `PRD.md` para especificaciones del producto
- **n8n Integration**: Ver `backend/N8N_INTEGRATION.md` para integración con chatbots

## 🛠️ Tecnologías Utilizadas

### Frontend
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui
- Vite
- Spark KV (almacenamiento local)

### Backend
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Python 3.11+

## 🐛 Troubleshooting

### "Error al conectar con el backend"

1. Verifica que el backend esté corriendo en http://localhost:8000
2. Prueba acceder a http://localhost:8000/docs directamente
3. Revisa la consola del navegador para ver errores CORS
4. Verifica que la URL en configuración sea correcta

### "Los cambios no se aplican"

Después de cambiar el modo de backend, **debes recargar la página** para que los cambios tengan efecto.

### "Datos duplicados después de cambiar backend"

Los datos del modo local y el modo API son **completamente independientes**. Cambiar de modo no migra datos automáticamente.

### "Stock negativo o inconsistente"

Si usas modo API, verifica que el backend esté usando transacciones atómicas correctamente. Los errores de stock indican un problema en el backend.

## 📄 Licencia

Ver archivo LICENSE en el directorio raíz del proyecto.
