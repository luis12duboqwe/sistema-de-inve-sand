#!/bin/bash

# Script de limpieza y organización de documentación v2.0
# Ejecutar con: ./cleanup_v2.sh

echo "🧹 Iniciando limpieza y organización..."

# 1. Crear directorio de documentación
mkdir -p docs

# 2. Mover documentación técnica valiosa
echo "📦 Moviendo documentación técnica a docs/..."

# Auditoría y Fixes
mv AUDITORIA_INICIAL.md docs/AUDITORIA.md 2>/dev/null
mv FASE_1.5_ARREGLADA.md docs/FIXES_FASE_1.md 2>/dev/null
mv FASE_2_RESUELTA.md docs/FIXES_FASE_2.md 2>/dev/null
mv VALIDACION_IMPLEMENTACIONES_COMPLETADA.md docs/VALIDACION.md 2>/dev/null

# Testing
mv TESTING_EXECUTION_PLAN.md docs/TESTING_PLAN.md 2>/dev/null
mv TESTING_RESULTS.md docs/TESTING_RESULTS.md 2>/dev/null
mv TESTING_GUIDE.md docs/GUIA_TESTING.md 2>/dev/null

# Deployment y Manuales
mv DEPLOYMENT_EXECUTION.md docs/DEPLOYMENT.md 2>/dev/null
mv TESTING_DEPLOYMENT_INSTRUCTIONS.md docs/MANUAL_COMPLETO.md 2>/dev/null
mv STOCK_TRANSFER_GUIDE.md docs/GUIA_TRANSFERENCIAS.md 2>/dev/null
mv INTEGRATION.md docs/INTEGRACION.md 2>/dev/null

# Arquitectura y Seguridad
mv NUEVO_SISTEMA_UBICACIONES.md docs/ARQUITECTURA.md 2>/dev/null
mv SECURITY.md docs/SEGURIDAD.md 2>/dev/null
mv PRD.md docs/PRD.md 2>/dev/null

# 3. Eliminar archivos redundantes/generados
echo "🗑️ Eliminando archivos redundantes..."

FILES_TO_DELETE=(
    "00_EMPEZAR_AQUI_PRIMERO.md"
    "ANALISIS_BUGS_Y_PROBLEMAS.md"
    "ARBOL_DOCUMENTACION.md"
    "AUDITORIA_COMPLETADA.md"
    "AUDITORIA_COMPLETADA_LISTO_TESTING.md"
    "BUGS_ADICIONALES_ENCONTRADOS.md"
    "CHECKLIST_EJECUCION.md"
    "CODE_CHANGES_SUMMARY.md"
    "COMIENZA_AQUI.md"
    "CONCLUSION_AUDITORIA_COMPLETADA.md"
    "CONCLUSION_FINAL.md"
    "CONCLUSION_SUPREMA.md"
    "CONFIRMACION_DE_ENTREGA.md"
    "CONFIRMACION_FINAL.md"
    "DASHBOARD_FINAL.md"
    "DEPLOYMENT_GUIDE.md"
    "DOCUMENTACION_INDICE.md"
    "DOCUMENTACION_MAESTRA.md"
    "EJECUCION_COMPLETADA.md"
    "ENTREGA_FINAL_AUDITORIA_COMPLETADA.md"
    "FASE2_COMPLETADA.md"
    "FASE3_ROADMAP.md"
    "FICHA_PROYECTO_FINAL.md"
    "FIXES_IMPLEMENTADOS.md"
    "GO_DEPLOY_NOW.md"
    "GUIA_INMEDIATA.md"
    "INDEX.md"
    "INDICE_AUDITORIA.md"
    "INDICE_MAESTRO.md"
    "INICIO_VISUAL.sh"
    "LISTADO_DOCUMENTOS_CREADOS.md"
    "LISTO_PARA_TESTING.md"
    "MAPA_FINAL.md"
    "MAPA_RAPIDO_UBICACIONES.md"
    "MAPA_VISUAL_PROBLEMAS.md"
    "PLAN_EJECUTADO_COMPLETAMENTE.md"
    "PLAN_SOLUCION_BUGS_CRITICOS.md"
    "PROGRESO_FINAL.md"
    "PROYECTO_COMPLETADO.md"
    "PROYECTO_COMPLETADO_RESUMEN.md"
    "QUICK_START_AUDITORIA.md"
    "QUICK_VERIFICATION.md"
    "README_AUDITORIA.md"
    "README_FINAL.md"
    "README_PROYECTO_COMPLETADO.md"
    "RECOMENDACIONES_ARQUITECTURA.md"
    "REFERENCIA_RAPIDA.md"
    "RESUMEN_EJECUTIVO_AUDITORIA.md"
    "RESUMEN_EJECUTIVO_FINAL.md"
    "RESUMEN_EJECUTIVO_LISTO_TESTING.md"
    "RESUMEN_FINAL_TODO_COMPLETADO.md"
    "RESUMEN_VISUAL.md"
    "START_HERE.md"
    "STATUS_REPORT.md"
    "TESTING_CHECKLIST_FIXES.md"
    "VISUAL_SUMMARY.md"
)

for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
    fi
done

echo "✅ Limpieza completada."
echo "📂 La documentación técnica se ha movido a la carpeta 'docs/'."
