# 🧪 Guía de Pruebas del Sistema

Este documento detalla cómo probar completamente el sistema de inventario.

## 📋 Pre-requisitos

- Node.js 18+ instalado
- Python 3.8+ instalado
- npm o yarn
- pip3

## 🚀 Inicio Rápido

### Opción 1: Script Automático

```bash
chmod +x test-system.sh
./test-system.sh
```

### Opción 2: Manual

#### Backend

```bash
# 1. Navegar al directorio backend
cd backend

# 2. Crear entorno virtual (solo primera vez)
python3 -m venv venv

# 3. Activar entorno virtual
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Inicializar base de datos (solo primera vez)
python3 init_db.py

# 6. Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

El backend estará disponible en:
- API: http://localhost:8000
- Documentación interactiva: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### Frontend

```bash
# 1. En la raíz del proyecto
npm install

# 2. Iniciar servidor de desarrollo
npm run dev
```

El frontend estará disponible en: http://localhost:5173

## ✅ Checklist de Pruebas

### 1. Autenticación y Perfiles

- [ ] **Crear primer perfil**
  - Abrir aplicación
  - Completar formulario de perfil inicial
  - Verificar que se guarda correctamente

- [ ] **Login**
  - Cerrar sesión
  - Iniciar sesión con credenciales del perfil
  - Verificar acceso al dashboard

- [ ] **Múltiples perfiles**
  - Crear 2-3 perfiles adicionales
  - Cambiar entre perfiles
  - Verificar que cada perfil tiene datos independientes

### 2. Gestión de Productos

- [ ] **Crear productos**
  - Click en "Nuevo Producto"
  - Completar formulario con datos válidos
  - Verificar que aparece en la lista

- [ ] **Editar productos**
  - Click en un producto
  - Modificar precio, stock, descripción
  - Guardar y verificar cambios

- [ ] **Eliminar productos**
  - Seleccionar producto
  - Confirmar eliminación
  - Verificar que desaparece de la lista

- [ ] **Búsqueda y filtros**
  - Buscar por nombre
  - Buscar por código de barras
  - Filtrar por categoría
  - Filtrar por stock bajo

- [ ] **Importar productos**
  - Usar botón de importación
  - Cargar archivo CSV/JSON
  - Verificar que se importan correctamente

### 3. Gestión de Pedidos

- [ ] **Crear pedido**
  - Click en "Nueva Venta"
  - Agregar productos
  - Verificar cálculo de totales
  - Completar venta

- [ ] **Ver historial**
  - Revisar lista de pedidos
  - Verificar fechas y montos
  - Abrir detalles de pedido

- [ ] **Editar pedido**
  - Modificar pedido pendiente
  - Cambiar estado
  - Verificar actualizaciones

- [ ] **Cancelar pedido**
  - Cancelar un pedido
  - Verificar que el stock se restaura

### 4. Dashboard y Estadísticas

- [ ] **Estadísticas generales**
  - Verificar ventas totales del día
  - Verificar cantidad de productos
  - Verificar productos con stock bajo

- [ ] **Gráficos**
  - Revisar gráfico de ventas
  - Verificar datos de los últimos 7 días
  - Comprobar responsividad

- [ ] **Alertas de stock bajo**
  - Verificar notificaciones
  - Click en alerta para ver productos
  - Verificar lista de productos con stock bajo

### 5. Funcionalidades Avanzadas

- [ ] **Predicción de ventas (AI)**
  - Abrir diálogo de predicciones
  - Verificar que muestra tendencias
  - Revisar recomendaciones

- [ ] **Insights de optimización**
  - Abrir panel de insights
  - Verificar análisis de productos
  - Revisar sugerencias

- [ ] **Historial de clientes**
  - Buscar cliente por teléfono
  - Ver historial de compras
  - Verificar datos agregados

- [ ] **Notificaciones**
  - Configurar notificaciones
  - Probar diferentes tipos de alertas
  - Verificar que se muestran correctamente

### 6. Atajos de Teclado

- [ ] `Ctrl+K` - Búsqueda rápida
- [ ] `Ctrl+N` - Nuevo producto
- [ ] `Ctrl+S` - Nueva venta
- [ ] `Ctrl+D` - Dashboard
- [ ] `Ctrl+P` - Productos
- [ ] `Ctrl+O` - Pedidos
- [ ] `?` - Ayuda de atajos

### 7. Responsive Design

- [ ] **Desktop** (1920x1080)
  - Verificar layout completo
  - Probar todas las funcionalidades

- [ ] **Tablet** (768x1024)
  - Verificar menú adaptativo
  - Comprobar diálogos

- [ ] **Mobile** (375x667)
  - Verificar navegación mobile
  - Probar gestos táctiles

### 8. Rendimiento

- [ ] **Carga inicial**
  - Medir tiempo de carga
  - Verificar que es < 3 segundos

- [ ] **Operaciones**
  - Crear 100+ productos
  - Crear 50+ pedidos
  - Verificar que no hay lag

- [ ] **Búsqueda**
  - Buscar con 1000+ productos
  - Verificar respuesta instantánea

### 9. Backend API

- [ ] **Endpoints de autenticación**
  - POST `/api/profiles` - Crear perfil
  - POST `/api/auth/login` - Login
  - GET `/api/auth/me` - Perfil actual

- [ ] **Endpoints de productos**
  - GET `/api/products` - Listar
  - POST `/api/products` - Crear
  - PUT `/api/products/{id}` - Actualizar
  - DELETE `/api/products/{id}` - Eliminar

- [ ] **Endpoints de pedidos**
  - GET `/api/orders` - Listar
  - POST `/api/orders` - Crear
  - PUT `/api/orders/{id}` - Actualizar
  - DELETE `/api/orders/{id}` - Cancelar

- [ ] **Health Check**
  - GET `/health` - Estado del sistema
  - Verificar respuesta 200 OK

### 10. Manejo de Errores

- [ ] **Validaciones**
  - Intentar crear producto sin nombre
  - Intentar venta con stock insuficiente
  - Verificar mensajes de error claros

- [ ] **Conexión perdida**
  - Detener backend temporalmente
  - Verificar mensajes de error
  - Reiniciar y verificar reconexión

- [ ] **Datos inválidos**
  - Introducir texto en campos numéricos
  - Introducir números negativos
  - Verificar validación en frontend y backend

## 🔍 Verificación de Logs

### Backend
Revisar terminal del backend para:
- Requests HTTP exitosos (200, 201)
- Errores de validación (400, 422)
- Errores de servidor (500)

### Frontend
Abrir DevTools (F12) y revisar:
- Console: No debe haber errores rojos
- Network: Verificar llamadas API
- Performance: Verificar tiempos de carga

## 📊 Criterios de Éxito

El sistema está funcionando correctamente si:

✅ Todos los endpoints del backend responden
✅ No hay errores en la consola del navegador
✅ Se pueden crear, editar y eliminar productos
✅ Se pueden realizar ventas y actualizar stock
✅ Las estadísticas se calculan correctamente
✅ Los múltiples perfiles funcionan independientemente
✅ La interfaz es responsive en todos los dispositivos
✅ Los atajos de teclado funcionan
✅ Las notificaciones se muestran apropiadamente

## 🐛 Problemas Comunes

### Backend no inicia
```bash
# Verificar que el puerto 8000 no está en uso
lsof -i :8000

# Matar proceso si es necesario
kill -9 <PID>
```

### Frontend no compila
```bash
# Limpiar cache y reinstalar
rm -rf node_modules package-lock.json
npm install
```

### Base de datos bloqueada
```bash
# Reiniciar backend
# Verificar que no hay múltiples instancias ejecutándose
ps aux | grep uvicorn
```

### Errores CORS
- Verificar que el backend está corriendo en el puerto correcto
- Revisar configuración en `backend/app/main.py`

## 📝 Reportar Problemas

Si encuentras problemas:

1. Anota los pasos para reproducir el error
2. Captura el mensaje de error completo
3. Revisa los logs del backend y frontend
4. Verifica la versión de Node.js y Python
5. Documenta el comportamiento esperado vs actual

## 🎯 Próximos Pasos

Una vez que todas las pruebas pasen:

1. Hacer backup de la base de datos
2. Configurar entorno de producción
3. Implementar medidas de seguridad adicionales
4. Configurar monitoreo y logs
5. Preparar documentación para usuarios finales
