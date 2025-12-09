#!/bin/bash

echo "Haciendo scripts ejecutables..."

chmod +x setup-complete.sh
chmod +x test-system.sh
chmod +x start-backend.sh
chmod +x start-frontend.sh
chmod +x validate-system.sh
chmod +x system-status.sh

echo "✅ Scripts ahora ejecutables"
echo ""
echo "Scripts disponibles:"
echo "  ./setup-complete.sh    - Configuración completa (primera vez)"
echo "  ./test-system.sh       - Verificar estado del sistema"
echo "  ./start-backend.sh     - Iniciar backend"
echo "  ./start-frontend.sh    - Iniciar frontend"
