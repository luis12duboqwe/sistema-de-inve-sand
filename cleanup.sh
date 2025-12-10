#!/bin/bash

# Script de limpieza de archivos innecesarios
# Sistema de Inventario V2.0

echo "🧹 Limpiando archivos innecesarios..."

# Archivos de documentación redundantes
rm -f 00_LEEME_PRIMERO.txt
rm -f BIENVENIDA.txt
rm -f CAMBIOS_REALIZADOS.md
rm -f CHECKLIST.sh
rm -f COMO_LEVANTAR_SISTEMA.md
rm -f ERROR_BLOQUEADOR.txt
rm -f FIX_PIP.md
rm -f GO.sh
rm -f INDEX.md
rm -f INSTRUCCIONES.sh
rm -f LEEME.txt
rm -f PERMISSIONS_FIX.md
rm -f PIP_MISSING.md
rm -f QUICK_START.md
rm -f QUICK_START_FINAL.md
rm -f READY.txt
rm -f RESUMEN_FINAL_SETUP.md
rm -f SCRIPTS_ACTUALIZADOS.md
rm -f SESION_COMPLETADA.md
rm -f SETUP_CHANGES_SUMMARY.md
rm -f SETUP_MANUAL.md
rm -f SISTEMA_100_COMPLETO.md
rm -f SOLUCION_PIP.txt
rm -f SOLUCION_PROBLEMAS.md
rm -f START.md
rm -f SUMMARY.md

# Scripts obsoletos de setup
rm -f diagnose-and-fix.py
rm -f fix-permissions.sh
rm -f fix_permissions.py
rm -f inicio.sh
rm -f install-pip.sh
rm -f make-executable.sh
rm -f make-scripts-executable.sh
rm -f quick-setup.sh
rm -f reset-venv.sh
rm -f reset_venv.py
rm -f setup-backend.sh
rm -f setup-complete.sh
rm -f setup-direct.py
rm -f setup-simple.py
rm -f setup.py
rm -f setup.sh
rm -f system-status.sh
rm -f validate-system.sh
rm -f create-stock.sh

echo "✅ Archivos eliminados"
echo ""
echo "📄 Documentación mantenida:"
echo "  - README.md (Documentación principal)"
echo "  - INICIO_RAPIDO.md (Guía de inicio)"
echo "  - PRD.md (Requisitos del producto)"
echo "  - NUEVO_SISTEMA_UBICACIONES.md (Arquitectura V2.0)"
echo "  - INTEGRATION.md (Guía de integración)"
echo "  - TESTING_GUIDE.md (Guía de pruebas)"
echo "  - STOCK_TRANSFER_GUIDE.md (Guía de transferencias)"
echo "  - SECURITY.md (Seguridad)"
echo "  - LICENSE (Licencia)"
echo ""
echo "🚀 Scripts mantenidos:"
echo "  - start-all.sh (Inicio completo)"
echo "  - start-backend.sh (Backend)"
echo "  - start-frontend.sh (Frontend)"
echo "  - start-backend-codespaces.sh (Codespaces)"
echo "  - test-system.sh (Pruebas)"
echo ""
echo "✨ Limpieza completada"
