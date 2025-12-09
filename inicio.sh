#!/bin/bash

# Script de entrada principal - El más simple posible

clear

cat << 'EOF'
╔══════════════════════════════════════════════════════════╗
║     🚀 SISTEMA DE INVENTARIO MULTI-UBICACIÓN V2.0       ║
╚══════════════════════════════════════════════════════════╝

EOF

echo "¿Qué deseas hacer?"
echo ""
echo "  1) 🎬 Iniciar el sistema (TODO EN UNO)"
echo "  2) ⚙️  Configurar por primera vez"
echo "  3) 🔍 Verificar estado del sistema"
echo "  4) 📖 Ver documentación"
echo "  5) ❌ Salir"
echo ""
read -p "Selecciona una opción [1-5]: " opcion

case $opcion in
    1)
        echo ""
        echo "🎬 Iniciando sistema completo..."
        chmod +x start-all.sh
        ./start-all.sh
        ;;
    2)
        echo ""
        echo "⚙️  Configurando sistema..."
        chmod +x setup-complete.sh
        ./setup-complete.sh
        ;;
    3)
        echo ""
        echo "🔍 Verificando sistema..."
        chmod +x test-system.sh
        ./test-system.sh
        ;;
    4)
        echo ""
        echo "📖 Documentación disponible:"
        echo ""
        echo "  • COMO_LEVANTAR_SISTEMA.md - Guía de inicio"
        echo "  • NUEVO_SISTEMA_UBICACIONES.md - Arquitectura V2.0"
        echo "  • README.md - Información general"
        echo "  • SCRIPTS_ACTUALIZADOS.md - Scripts disponibles"
        echo ""
        echo "Abre cualquiera de estos archivos en VS Code"
        echo ""
        read -p "Presiona Enter para continuar..."
        ;;
    5)
        echo ""
        echo "👋 ¡Hasta luego!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ Opción inválida"
        exit 1
        ;;
esac
