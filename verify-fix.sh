#!/bin/bash

echo "🔍 Verificación Rápida del Sistema"
echo "=================================="
echo ""

# Verificar si el backend está corriendo
echo "📡 Verificando conexión del backend..."
if curl -s http://localhost:8000/api/profiles > /dev/null 2>&1; then
    echo "✅ Backend está corriendo en http://localhost:8000"
    
    # Mostrar respuesta
    echo ""
    echo "📊 Respuesta del endpoint /profiles:"
    curl -s http://localhost:8000/api/profiles | jq . 2>/dev/null || curl -s http://localhost:8000/api/profiles
else
    echo "❌ Backend NO está corriendo"
    echo ""
    echo "Para iniciar el backend, ejecuta:"
    echo "  bash /workspaces/spark-template/run-backend-direct.sh"
fi

echo ""
echo "=================================="
echo ""

# Verificar archivos críticos modificados
echo "📁 Verificando archivos modificados..."
if [ -f "/workspaces/spark-template/src/lib/apiClient.ts" ]; then
    echo "✅ apiClient.ts existe"
else
    echo "❌ apiClient.ts NO encontrado"
fi

if [ -f "/workspaces/spark-template/src/components/BackendConnectionCheck.tsx" ]; then
    echo "✅ BackendConnectionCheck.tsx existe"
else
    echo "❌ BackendConnectionCheck.tsx NO encontrado"
fi

echo ""
echo "🎯 Próximo paso: Recarga el frontend para aplicar los cambios"
echo ""
