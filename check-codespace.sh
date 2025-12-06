#!/bin/bash

echo "🔧 Configuración de Puertos en Codespace"
echo "=========================================="
echo ""

# Detectar si estamos en un Codespace
if [ -n "$CODESPACE_NAME" ]; then
    echo "✅ Codespace detectado: $CODESPACE_NAME"
    echo ""
    
    # Información del entorno
    echo "📡 Información del entorno:"
    echo "  - Codespace Name: $CODESPACE_NAME"
    echo "  - GitHub User: $GITHUB_USER"
    if [ -n "$CODESPACE_VSCODE_FOLDER" ]; then
        echo "  - Workspace: $CODESPACE_VSCODE_FOLDER"
    fi
    echo ""
    
    # Verificar si gh CLI está disponible
    if command -v gh &> /dev/null; then
        echo "✅ GitHub CLI (gh) disponible"
        echo ""
        echo "📋 Puertos expuestos actualmente:"
        gh codespace ports -c "$CODESPACE_NAME" 2>/dev/null || echo "  (No se pudo listar puertos)"
        echo ""
    else
        echo "⚠️  GitHub CLI (gh) no disponible"
        echo ""
    fi
    
    # Instrucciones para hacer el puerto público
    echo "🔓 Para hacer el puerto 8000 público:"
    echo ""
    echo "1. En VS Code, ve a la pestaña 'PORTS' (abajo)"
    echo "2. Busca el puerto 8000"
    echo "3. Click derecho -> 'Port Visibility' -> 'Public'"
    echo ""
    echo "O usa este comando:"
    echo "  gh codespace ports visibility 8000:public -c \"$CODESPACE_NAME\""
    echo ""
    
    # Verificar si el backend está corriendo
    echo "🔍 Verificando si el backend está corriendo..."
    if pgrep -f "uvicorn.*main:app" > /dev/null; then
        echo "✅ Backend está corriendo"
        
        # Probar conexión local
        echo ""
        echo "🧪 Probando conexión local..."
        if curl -s http://localhost:8000/api/profiles > /dev/null 2>&1; then
            echo "✅ Backend responde en http://localhost:8000/api"
        else
            echo "❌ Backend NO responde en http://localhost:8000/api"
        fi
    else
        echo "❌ Backend NO está corriendo"
        echo ""
        echo "Para iniciar el backend:"
        echo "  bash /workspaces/spark-template/run-backend-direct.sh"
    fi
    
else
    echo "ℹ️  No estás en un Codespace de GitHub"
    echo ""
    echo "Verificando backend local..."
    
    if curl -s http://localhost:8000/api/profiles > /dev/null 2>&1; then
        echo "✅ Backend responde en http://localhost:8000/api"
    else
        echo "❌ Backend NO responde en http://localhost:8000/api"
    fi
fi

echo ""
echo "=========================================="
echo "✅ Verificación completada"
