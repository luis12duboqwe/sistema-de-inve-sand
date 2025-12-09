#!/usr/bin/env bash
# SETUP CHECKLIST - Verifica cada paso del proceso

cat << 'EOF'

╔══════════════════════════════════════════════════════════╗
║  ✓ CHECKLIST DE SETUP - SISTEMA V2.0                    ║
║    Marca cada paso conforme lo completes                ║
╚══════════════════════════════════════════════════════════╝

📋 ANTES DE EMPEZAR
┌─────────────────────────────────────────────────────────┐
│ ☐ Tienes Python 3.11+    (python3 --version)
│ ☐ Tienes Node.js 18+     (node --version)
│ ☐ Tienes npm 9+          (npm --version)
│ ☐ Tienes 500MB de espacio en disco libre
│ ☐ Estás en la carpeta correcta (/workspaces/spark-template)
└─────────────────────────────────────────────────────────┘

🔧 INSTALACIÓN
┌─────────────────────────────────────────────────────────┐
│ ☐ Ejecuté: bash setup.sh
│ ☐ Esperé a que termine (2-3 minutos)
│ ☐ Vi el mensaje ✅ SETUP COMPLETADO
│ ☐ Vi el mensaje ✅ npm iniciado en background
└─────────────────────────────────────────────────────────┘

🚀 INICIO DE SERVICIOS
┌─────────────────────────────────────────────────────────┐
│ Terminal 1 - Backend
│ ☐ Ejecuté: ./start-backend.sh
│ ☐ Vi: ✅ Python X.X.X encontrado
│ ☐ Vi: 🚀 Iniciando FastAPI en puerto 8000
│ ☐ Déjé la terminal abierta (no cierres)
│
│ Terminal 2 - Frontend
│ ☐ Ejecuté: ./start-frontend.sh
│ ☐ Vi: ✅ Node.js vXX.X.X encontrado
│ ☐ Vi: 🚀 Iniciando servidor Vite
│ ☐ Déjé la terminal abierta (no cierres)
│
│ Terminal 3 - Navegador
│ ☐ Abrí: http://localhost:5173
│ ☐ Cargó la aplicación React
└─────────────────────────────────────────────────────────┘

✅ VERIFICACIÓN
┌─────────────────────────────────────────────────────────┐
│ ☐ Backend responde: curl http://localhost:8000/docs
│ ☐ Frontend cargó sin errores
│ ☐ Vi la interfaz de la app (Products, Orders, Settings)
│ ☐ No hay errores en la consola del navegador (F12)
│ ☐ No hay errores rojos en las terminales
└─────────────────────────────────────────────────────────┘

🎯 PRIMERA CONFIGURACIÓN
┌─────────────────────────────────────────────────────────┐
│ ☐ Abrí Settings (⚙️ esquina superior derecha)
│ ☐ Creé primera ubicación (Locations → Add New)
│   └─ Nombre: Tienda 1, Tipo: tienda
│ ☐ Creé primer perfil de ventas (Sales Profiles → Add New)
│   └─ Nombre: Bot Principal, Tipo: bot_ia
│ ☐ Cambié de Mode (Settings → "Usar API backend") si es necesario
│   └─ En Local Mode: Datos en navegador
│   └─ En API Mode: Datos en servidor
└─────────────────────────────────────────────────────────┘

📦 PRIMER PRODUCTO
┌─────────────────────────────────────────────────────────┐
│ ☐ Fui a: Products
│ ☐ Hice clic en: Add Product (Ctrl+N)
│ ☐ Ingresé datos:
│   └─ Nombre: "iPhone 15"
│   └─ Marca: Apple
│   └─ Categoría: celular
│   └─ Precio: 999.99
│   └─ Stock: 10
│   └─ Ubicación: Tienda 1 (de arriba)
│ ☐ Hice clic en: Create Product
│ ☐ Vi mensaje ✅ "Producto creado exitosamente"
│ ☐ Vi el producto en la lista
└─────────────────────────────────────────────────────────┘

🛒 PRIMERA ORDEN
┌─────────────────────────────────────────────────────────┐
│ ☐ Fui a: Orders
│ ☐ Hice clic en: New Order (Ctrl+O)
│ ☐ Seleccioné:
│   └─ Perfil de Ventas: Bot Principal
│   └─ Ubicación de Origen: Tienda 1
│   └─ Canal: WhatsApp
│ ☐ Ingresé cliente:
│   └─ Nombre: Juan Pérez
│   └─ Teléfono: +504 99999999
│ ☐ Agregué producto:
│   └─ Producto: iPhone 15
│   └─ Cantidad: 2
│ ☐ Seleccioné método de pago: Efectivo
│ ☐ Hice clic en: Create Order
│ ☐ Vi mensaje ✅ "Orden creada exitosamente"
│ ☐ Stock se redujo a 8 (era 10, vendí 2)
└─────────────────────────────────────────────────────────┘

🔄 STOCK TRANSFER (Bonus)
┌─────────────────────────────────────────────────────────┐
│ ☐ Fui a: Products
│ ☐ En tarjeta del producto hice clic en: "Stock by Location"
│ ☐ Hice clic en: "Transfer"
│ ☐ Seleccioné:
│   └─ From: Tienda 1
│   └─ To: Bodega Central (o crear nueva)
│   └─ Cantidad: 3
│ ☐ Hice clic en: Transfer
│ ☐ Vi el cambio en el stock de ambas ubicaciones
└─────────────────────────────────────────────────────────┘

🎉 FINAL - TODO LISTO!
┌─────────────────────────────────────────────────────────┐
│ ✅ Sistema funcionando 100%
│ ✅ Base de datos sincronizada
│ ✅ Usuarios satisfechos
│
│ Próximos pasos:
│ • Agregar más ubicaciones
│ • Agregar más productos
│ • Configurar más perfiles de venta
│ • Conectar canales reales (WhatsApp, Facebook, etc)
│ • Explorar reportes y analytics
└─────────────────────────────────────────────────────────┘

❌ SI ALGO FALLA
┌─────────────────────────────────────────────────────────┐
│ 1. Mira los logs en las terminales (líneas rojas)
│ 2. Lee: START.md → Sección "Troubleshooting"
│ 3. Intenta: Limpiar y reinstalar
│    rm -rf backend/inventory.db backend/venv node_modules
│    bash setup.sh
│ 4. Lee: SETUP_MANUAL.md para instrucciones detalladas
│ 5. Ejecuta: bash validate-system.sh para validar
└─────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 ¡FELICIDADES! Has completado el setup.

¿Qué sigue?
→ Agrega más productos
→ Haz más órdenes
→ Explora todas las características de V2.0
→ Lee la documentación en .github/copilot-instructions.md

Happy Inventory Managing! 📦✨

EOF
