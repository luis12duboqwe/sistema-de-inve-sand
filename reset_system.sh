#!/bin/bash

# Script para reiniciar el sistema desde cero
# Elimina la base de datos y la recrea vacía

echo "🛑 Deteniendo servicios del backend..."
pkill -f "uvicorn" || true

echo "🗑️ Eliminando base de datos actual..."
rm -f backend/inventory.db

echo "✨ Inicializando nueva base de datos (tablas vacías)..."
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
fi
# Aseguramos que NO se use --with-data
python3 init_db.py

echo "🚀 Reiniciando el backend..."
cd ..
# Ejecutamos en segundo plano
nohup ./start-backend.sh > backend_reset.log 2>&1 &

echo ""
echo "✅ ¡Sistema reiniciado exitosamente!"
echo "----------------------------------------"
echo "La base de datos ha sido limpiada."
echo "Para comenzar a usar el sistema:"
echo "1. Recarga la página web (F5)"
echo "2. Crea una 'Ubicación' (ej. Tienda Principal)"
echo "3. Crea un 'Perfil de Venta' (ej. Vendedor 1)"
echo "----------------------------------------"
