#!/bin/bash

echo "🔧 Instalando dependencias del sistema..."
echo ""

# Actualizar lista de paquetes
echo "1️⃣  Actualizando lista de paquetes..."
sudo apt update

# Instalar python3-venv
echo ""
echo "2️⃣  Instalando python3-venv..."
sudo apt install -y python3.11-venv python3-pip

echo ""
echo "✅ Dependencias del sistema instaladas"
echo ""
echo "Ahora ejecuta:"
echo "  bash /workspaces/spark-template/setup-backend.sh"
echo ""
