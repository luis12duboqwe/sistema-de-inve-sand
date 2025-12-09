#!/bin/bash

echo "🧪 PROBANDO NUEVO SISTEMA DE UBICACIONES"
echo "========================================="
echo ""

BASE_URL="http://localhost:8000"

echo "1️⃣  Verificando que el backend esté corriendo..."
if curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
    echo "   ✅ Backend activo"
else
    echo "   ❌ Backend no está corriendo"
    echo "   Ejecuta: cd backend && python3 -m uvicorn app.main:app --reload"
    exit 1
fi

echo ""
echo "2️⃣  Probando endpoint de Locations..."
response=$(curl -s "${BASE_URL}/api/locations")
if [ $? -eq 0 ]; then
    echo "   ✅ GET /api/locations funcional"
    echo "   Ubicaciones actuales: $(echo $response | grep -o '"id"' | wc -l)"
else
    echo "   ❌ Error en /api/locations"
fi

echo ""
echo "3️⃣  Probando endpoint de Sales Profiles..."
response=$(curl -s "${BASE_URL}/api/sales-profiles")
if [ $? -eq 0 ]; then
    echo "   ✅ GET /api/sales-profiles funcional"
    echo "   Perfiles de venta: $(echo $response | grep -o '"id"' | wc -l)"
else
    echo "   ❌ Error en /api/sales-profiles"
fi

echo ""
echo "4️⃣  Creando ubicación de prueba..."
location_data='{
  "nombre": "Tienda Test",
  "tipo": "tienda",
  "direccion": "Calle de Prueba #123",
  "activo": true
}'

response=$(curl -s -X POST "${BASE_URL}/api/locations" \
  -H "Content-Type: application/json" \
  -d "$location_data")

if echo "$response" | grep -q '"id"'; then
    location_id=$(echo "$response" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
    echo "   ✅ Ubicación creada con ID: $location_id"
else
    echo "   ⚠️  No se pudo crear ubicación (puede que ya exista)"
fi

echo ""
echo "5️⃣  Creando perfil de venta de prueba..."
profile_data='{
  "name": "Bot de Prueba",
  "slug": "bot-prueba-'$(date +%s)'",
  "tipo": "bot_ia",
  "canales": ["whatsapp"],
  "active": true
}'

response=$(curl -s -X POST "${BASE_URL}/api/sales-profiles" \
  -H "Content-Type: application/json" \
  -d "$profile_data")

if echo "$response" | grep -q '"id"'; then
    profile_id=$(echo "$response" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
    echo "   ✅ Perfil de venta creado con ID: $profile_id"
else
    echo "   ⚠️  No se pudo crear perfil"
fi

echo ""
echo "========================================="
echo "✅ PRUEBAS COMPLETADAS"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Ejecuta la migración: python3 backend/migrate_to_locations_model.py"
echo "   2. Revisa la documentación: NUEVO_SISTEMA_UBICACIONES.md"
echo "   3. Configura tus ubicaciones y perfiles de venta"
echo ""
echo "📚 Documentación:"
echo "   • API Docs: ${BASE_URL}/docs"
echo "   • Locations: ${BASE_URL}/api/locations"
echo "   • Sales Profiles: ${BASE_URL}/api/sales-profiles"
