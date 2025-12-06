@echo off
REM Script de inicio rápido del frontend para Windows

echo 🚀 Iniciando Frontend...
echo.

REM Verificar si existen node_modules
if not exist "node_modules\" (
    echo 📦 Instalando dependencias...
    call npm install
)

REM Iniciar servidor de desarrollo
echo.
echo ✅ Todo listo! Iniciando servidor de desarrollo...
echo 🌐 URL: http://localhost:5173
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

call npm run dev
