#!/usr/bin/env python3
"""
Script para limpiar y recrear el entorno virtual de Python.
Resuelve problemas de permisos en el venv.
"""

import os
import sys
import subprocess
import shutil

def clean_venv():
    """Elimina el entorno virtual antiguo."""
    venv_path = "./backend/venv"
    
    if os.path.exists(venv_path):
        print(f"🗑️  Eliminando entorno virtual antiguo: {venv_path}")
        try:
            shutil.rmtree(venv_path)
            print("✅ Entorno virtual eliminado")
            return True
        except Exception as e:
            print(f"⚠️  Error al eliminar: {e}")
            return False
    else:
        print("ℹ️  No hay entorno virtual anterior")
        return True

def create_venv():
    """Crea un nuevo entorno virtual."""
    print("\n📦 Creando nuevo entorno virtual...")
    
    try:
        result = subprocess.run(
            ["python3", "-m", "venv", "backend/venv"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ Entorno virtual creado")
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def install_dependencies():
    """Instala las dependencias."""
    print("\n📥 Instalando dependencias...")
    
    # Detectar el sistema operativo
    if sys.platform == "win32":
        pip_exe = "backend\\venv\\Scripts\\pip.exe"
    else:
        pip_exe = "backend/venv/bin/pip"
    
    try:
        # Actualizar pip
        print("   Actualizando pip...")
        result = subprocess.run(
            [pip_exe, "install", "--upgrade", "pip"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="."
        )
        
        if result.returncode != 0:
            print(f"⚠️  Warning al actualizar pip: {result.stderr[:100]}")
        
        # Instalar requirements
        print("   Instalando packages...")
        result = subprocess.run(
            [pip_exe, "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd="backend"
        )
        
        if result.returncode == 0:
            print("✅ Dependencias instaladas")
            return True
        else:
            print(f"❌ Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Timeout: La instalación tardó demasiado")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def initialize_database():
    """Inicializa la base de datos."""
    print("\n🗄️  Inicializando base de datos...")
    
    if sys.platform == "win32":
        python_exe = "backend\\venv\\Scripts\\python.exe"
    else:
        python_exe = "backend/venv/bin/python"
    
    try:
        result = subprocess.run(
            [python_exe, "init_db.py", "--with-data"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="backend"
        )
        
        if result.returncode == 0:
            print("✅ Base de datos inicializada")
            return True
        else:
            print(f"⚠️  Warning: {result.stderr[:100]}")
            # No fallamos aquí porque la BD se puede crear automáticamente
            return True
    except Exception as e:
        print(f"⚠️  Warning: {e}")
        return True

def main():
    print("═" * 60)
    print("🔧 LIMPIEZA Y CONFIGURACIÓN DEL ENTORNO VIRTUAL")
    print("═" * 60)
    print()
    
    # Cambiar al directorio raíz
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Ejecutar pasos
    if not clean_venv():
        print("\n❌ No se pudo limpiar el venv anterior")
        sys.exit(1)
    
    if not create_venv():
        print("\n❌ No se pudo crear el venv")
        sys.exit(1)
    
    if not install_dependencies():
        print("\n❌ No se pudieron instalar las dependencias")
        sys.exit(1)
    
    if not initialize_database():
        print("\n⚠️  Advertencia: No se pudo inicializar la BD")
    
    print()
    print("═" * 60)
    print("✅ CONFIGURACIÓN COMPLETADA")
    print("═" * 60)
    print()
    print("Ahora puedes ejecutar:")
    print("  ./start-backend.sh   - Iniciar el backend")
    print("  ./start-frontend.sh  - Iniciar el frontend")
    print()

if __name__ == "__main__":
    main()
