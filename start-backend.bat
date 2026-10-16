@echo off
REM Script de inicio rápido del backend para Windows - Sistema V2.0

echo 🚀 Iniciando Backend (Sistema de Inventario Multi-Ubicación V2.0)...
echo.

cd /d "%~dp0backend"

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python no está instalado
    echo    Instala Python 3.11+ desde https://www.python.org/
    pause
    exit /b 1
)

echo ✅ Python encontrado

REM Crear entorno virtual si no existe
if not exist "venv\" (
    echo 📦 Creando entorno virtual...
    python -m venv venv
    echo ✅ Entorno virtual creado
)

REM Activar entorno virtual
echo ⚡ Activando entorno virtual...
call venv\Scripts\activate.bat

REM Actualizar pip silenciosamente
python -m pip install --upgrade pip -q >nul 2>&1

REM Instalar dependencias
echo 📥 Verificando dependencias...
pip install -q -r requirements.txt

REM No ejecutar init_db.py --with-data en el arranque.
REM La API administra migraciones y esquema bajo lock; el seeding de demo
REM es una operacion manual exclusivamente para entornos descartables.

REM Iniciar servidor
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ✅ Servidor backend iniciado exitosamente
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🌐 API REST:        http://localhost:8000
echo 📚 Documentación:   http://localhost:8000/docs
echo 📖 ReDoc:           http://localhost:8000/redoc
echo.
echo 💡 Para detener: Ctrl+C
echo.

python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
