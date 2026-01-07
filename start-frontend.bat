@echo off
REM Script de inicio rápido del frontend para Windows - Sistema V2.0

echo 🚀 Iniciando Frontend (React + TypeScript + Vite)...
echo.

REM Verificar Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Node.js no está instalado
    echo    Instala Node.js 18+ desde https://nodejs.org/
    pause
    exit /b 1
)

npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: npm no está instalado
    pause
    exit /b 1
)

echo ✅ Node.js encontrado
echo ✅ npm encontrado

REM Verificar/instalar dependencias
if not exist "node_modules\" (
    echo.
    echo 📦 Instalando dependencias (primera vez)...
    echo    Esto puede tomar unos minutos...
    call npm install
    echo ✅ Dependencias instaladas
) else (
    echo ✅ Dependencias ya instaladas
)

REM Iniciar servidor de desarrollo
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ✅ Servidor de desarrollo iniciado exitosamente
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🌐 Aplicación:      http://localhost:5173
echo ⚡ HMR:             Habilitado (recarga automática)
echo.
echo 💡 Para detener: Ctrl+C
echo.
echo 📝 Modos de operación:
echo    • Local Mode:  Usa Spark KV (IndexedDB + localStorage)
echo    • API Mode:    Conecta con backend en http://localhost:8000
echo    (Configurable en Ajustes dentro de la app)
echo.

call npm run dev
