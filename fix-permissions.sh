#!/bin/bash
# Script para dar permisos de ejecución a todos los scripts

echo "🔐 Dando permisos de ejecución a los scripts..."

# Hacer ejecutables los scripts de raíz
chmod +x /workspaces/spark-template/start-backend.sh 2>/dev/null || true
chmod +x /workspaces/spark-template/start-frontend.sh 2>/dev/null || true
chmod +x /workspaces/spark-template/setup-backend.sh 2>/dev/null || true
chmod +x /workspaces/spark-template/test-system.sh 2>/dev/null || true

# Hacer ejecutable el script del backend
chmod +x /workspaces/spark-template/backend/start.sh 2>/dev/null || true

echo "✅ Permisos configurados!"
echo ""
echo "Ahora puedes ejecutar:"
echo "  ./start-backend.sh   - Iniciar el backend"
echo "  ./start-frontend.sh  - Iniciar el frontend"
echo "  ./test-system.sh     - Probar el sistema"
