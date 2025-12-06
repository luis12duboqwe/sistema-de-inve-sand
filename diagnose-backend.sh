#!/bin/bash

echo "🔍 Diagnóstico de Conectividad del Backend"
echo "=========================================="
echo ""

# Información del sistema
echo "📡 Información de Red:"
echo "  Hostname: $(hostname)"
echo "  IP Interna: $(hostname -I | awk '{print $1}')"
echo ""

# Verificar si el backend está corriendo
echo "🔍 Verificando proceso del backend..."
if pgrep -f "uvicorn.*main:app" > /dev/null; then
    echo "✅ Proceso uvicorn encontrado"
    echo ""
    echo "Detalles del proceso:"
    ps aux | grep -E "uvicorn.*main:app" | grep -v grep
else
    echo "❌ No se encontró proceso uvicorn"
fi

echo ""
echo "=========================================="
echo ""

# Probar diferentes URLs
echo "🧪 Probando conectividad a diferentes URLs:"
echo ""

urls=(
    "http://localhost:8000/api/profiles"
    "http://127.0.0.1:8000/api/profiles"
    "http://0.0.0.0:8000/api/profiles"
)

for url in "${urls[@]}"; do
    echo -n "  Probando $url ... "
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "$url" 2>/dev/null | grep -q "200"; then
        echo "✅ OK"
    else
        echo "❌ FALLO"
    fi
done

echo ""
echo "=========================================="
echo ""

# Mostrar puertos en escucha
echo "📊 Puertos en escucha en el puerto 8000:"
netstat -tlnp 2>/dev/null | grep ":8000" || ss -tlnp 2>/dev/null | grep ":8000" || echo "No se pudo obtener información de puertos"

echo ""
echo "=========================================="
echo ""

# Test directo con curl
echo "📥 Respuesta del endpoint /profiles (usando localhost):"
curl -s http://localhost:8000/api/profiles 2>&1 | head -c 500 || echo "Error al conectar"

echo ""
echo ""
echo "=========================================="
echo "✅ Diagnóstico completado"
