@echo off
REM Script de inicio rápido del backend para Windows

echo 🚀 Iniciando Backend...
echo.

cd backend

REM Verificar si existe el entorno virtual
if not exist "venv\" (
    echo 📦 Creando entorno virtual...
    python -m venv venv
)

REM Activar entorno virtual
echo ⚡ Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar dependencias
echo 📥 Instalando dependencias...
pip install -q -r requirements.txt

REM Inicializar base de datos si no existe
if not exist "inventory.db" (
    echo 🗄️  Inicializando base de datos...
    python init_db.py
)

REM Iniciar servidor
echo.
echo ✅ Todo listo! Iniciando servidor en http://localhost:8000
echo 📚 Documentación API: http://localhost:8000/docs
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

uvicorn app.main:app --reload --port 8000
