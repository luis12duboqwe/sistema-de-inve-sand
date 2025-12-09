#!/usr/bin/env bash
# This file is just instructions - read it, don't execute it!

# ============================================================
# 🚀 SISTEMA DE INVENTARIO V2.0 - INSTRUCCIONES DE INICIO
# ============================================================

# PASO 1: SETUP INICIAL (Una sola vez)
# Ejecuta en la terminal:
bash setup.sh

# Espera a que termine. Verás:
# ✅ Permisos configurados
# ✅ Limpieza completada
# ✅ Dependencias Python instaladas
# ✅ BD creada
# ✅ npm iniciado en background
# ✅ SETUP COMPLETADO

# ============================================================

# PASO 2: BACKEND (Terminal 1)
# Abre una NUEVA terminal y ejecuta:
./start-backend.sh

# Verás:
# ✅ Python X.X.X encontrado
# 📦 Verificando dependencias...
# 🚀 Iniciando FastAPI en puerto 8000...
# 📍 URLs:
#    API: http://localhost:8000
#    Swagger: http://localhost:8000/docs

# ✅ DÉJALO CORRIENDO (no cierres esta terminal)

# ============================================================

# PASO 3: FRONTEND (Terminal 2)
# Abre OTRA NUEVA terminal y ejecuta:
./start-frontend.sh

# Verás:
# ✅ Node.js vXX.X.X encontrado
# ✅ npm X.X.X encontrado
# 🚀 Iniciando servidor Vite...
# 🌐 Aplicación: http://localhost:5173

# ============================================================

# PASO 4: ABRE EL NAVEGADOR
# Visita:
# http://localhost:5173

# ============================================================

# ❌ Si algo falla:

# Opción A: Leer documentación
# cat START.md

# Opción B: Setup manual
# cd backend
# python3 -m pip install -r requirements.txt
# python3 init_db.py --with-data
# cd ..
# npm install

# Opción C: Limpiar todo y reintentar
# rm -rf backend/inventory.db backend/venv node_modules
# bash setup.sh
# ./start-backend.sh   # Terminal 1
# ./start-frontend.sh  # Terminal 2

# ============================================================

# ✨ ¡Listo! El sistema está corriendo
# 
# Ahora puedes:
# 1. Crear ubicaciones (Tienda, Bodega)
# 2. Crear perfiles de venta (Bot, Vendedor)
# 3. Agregar productos
# 4. Hacer órdenes
# 5. Transferir stock entre ubicaciones
#
# ¡Happy Inventory Managing! 📦

# ============================================================
