@echo off
echo 🚀 Iniciando Sistema de Inventario API
echo ========================================
echo.

if not exist "venv" (
    echo 📦 Creando entorno virtual...
    python -m venv venv
)

echo 🔧 Activando entorno virtual...
call venv\Scripts\activate

echo 📥 Instalando dependencias...
pip install -r requirements.txt

echo.
echo ✅ Instalación completa
echo.
echo 🌐 Iniciando servidor...
echo    API: http://localhost:8000
echo    Docs: http://localhost:8000/docs
echo.
echo 💡 Para inicializar datos de ejemplo:
echo    curl -X POST http://localhost:8000/api/init-data
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
