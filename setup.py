#!/usr/bin/env python3
"""
Script de setup completo para preparar el sistema desde cero.
Resuelve todos los problemas de permisos y dependencias.
"""

import os
import sys
import subprocess
import shutil
import stat

def print_section(title):
    """Imprime un título de sección."""
    print()
    print("=" * 60)
    print(f"🔧 {title}")
    print("=" * 60)

def chmod_scripts():
    """Da permisos de ejecución a los scripts."""
    print("1️⃣  Dando permisos de ejecución a scripts...")
    
    scripts = [
        "start-backend.sh",
        "start-frontend.sh",
        "setup-backend.sh",
        "test-system.sh",
        "backend/start.sh",
        "fix-permissions.sh",
        "reset-venv.sh",
    ]
    
    for script in scripts:
        try:
            if os.path.exists(script):
                # Dar permisos de ejecución
                st = os.stat(script)
                os.chmod(script, st.st_mode | stat.S_IEXEC | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                print(f"   ✓ {script}")
        except Exception as e:
            print(f"   ⚠️  {script}: {e}")
    
    print("✅ Permisos configurados")

def clean_venv():
    """Limpia el venv antiguo."""
    print("2️⃣  Limpiando entorno virtual antiguo...")
    
    venv_path = "backend/venv"
    if os.path.exists(venv_path):
        try:
            shutil.rmtree(venv_path)
            print("   ✓ Venv eliminado")
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
    else:
        print("   ℹ️  No hay venv anterior")
    
    print("✅ Limpieza completada")

def create_venv():
    """Crea un nuevo entorno virtual."""
    print("3️⃣  Creando entorno virtual...")
    
    # Cambiar a directorio backend
    os.chdir("backend")
    
    try:
        # Intentar crear venv
        result = subprocess.run(
            [sys.executable, "-m", "venv", "venv"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"   ⚠️  Error: {result.stderr[:100]}")
            print("   Intentando alternativa con --system-site-packages...")
            
            result = subprocess.run(
                [sys.executable, "-m", "venv", "venv", "--system-site-packages"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"   ❌ Error: {result.stderr[:200]}")
                os.chdir("..")
                return False
        
        # Verificar que se creó
        if not os.path.exists("venv"):
            print("   ❌ El directorio venv no se creó")
            os.chdir("..")
            return False
        
        print("   ✓ Venv creado")
        print("✅ Entorno virtual creado")
        os.chdir("..")
        return True
        
    except subprocess.TimeoutExpired:
        print("   ❌ Timeout: La creación tardó demasiado")
        os.chdir("..")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        os.chdir("..")
        return False

def install_dependencies():
    """Instala las dependencias de Python."""
    print("4️⃣  Instalando dependencias de Python...")
    
    # Detectar sistema operativo
    if sys.platform == "win32":
        pip_exe = os.path.join("venv", "Scripts", "pip.exe")
        python_exe = os.path.join("venv", "Scripts", "python.exe")
    else:
        pip_exe = os.path.join("venv", "bin", "pip")
        python_exe = os.path.join("venv", "bin", "python")
    
    # Cambiar a directorio backend
    os.chdir("backend")
    
    try:
        # Verificar que pip existe
        if not os.path.exists(pip_exe):
            print(f"   ⚠️  pip no encontrado en {pip_exe}")
            print("   Intentando usar python -m pip...")
            pip_exe = python_exe + " -m pip"
        
        # Actualizar pip
        print("   Actualizando pip...")
        result = subprocess.run(
            f"{pip_exe} install --upgrade pip -q",
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            print(f"   ⚠️  Warning al actualizar pip: {result.stderr[:50]}")
        
        # Instalar requirements
        print("   Instalando packages (esto puede tomar un minuto)...")
        result = subprocess.run(
            f"{pip_exe} install -r requirements.txt",
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            print(f"   ❌ Error: {result.stderr[:200]}")
            os.chdir("..")
            return False
        
        print("   ✓ Packages instalados")
        
        # Verificar FastAPI
        print("   Verificando FastAPI...")
        result = subprocess.run(
            f"{python_exe} -c \"import fastapi; print(fastapi.__version__)\"",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"   ✓ FastAPI {result.stdout.strip()}")
        else:
            print("   ⚠️  FastAPI no se verificó")
        
        print("✅ Dependencias de Python instaladas")
        os.chdir("..")
        return True
        
    except subprocess.TimeoutExpired:
        print("   ❌ Timeout: La instalación tardó demasiado")
        os.chdir("..")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        os.chdir("..")
        return False

def init_database():
    """Inicializa la base de datos."""
    print("5️⃣  Inicializando base de datos...")
    
    if sys.platform == "win32":
        python_exe = os.path.join("venv", "Scripts", "python.exe")
    else:
        python_exe = os.path.join("venv", "bin", "python")
    
    os.chdir("backend")
    
    try:
        db_exists = os.path.exists("inventory.db")
        
        if not db_exists:
            print("   Creando BD con datos de ejemplo...")
            result = subprocess.run(
                f"{python_exe} init_db.py --with-data",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("   ✓ BD creada")
            else:
                print(f"   ⚠️  Warning: {result.stderr[:100]}")
        else:
            print("   ℹ️  BD ya existe")
        
        print("✅ Base de datos lista")
        os.chdir("..")
        return True
        
    except subprocess.TimeoutExpired:
        print("   ❌ Timeout al inicializar BD")
        os.chdir("..")
        return False
    except Exception as e:
        print(f"   ⚠️  Warning: {e}")
        os.chdir("..")
        return True  # No es crítico

def install_frontend():
    """Instala las dependencias del frontend."""
    print("6️⃣  Preparando frontend...")
    
    if not os.path.exists("node_modules"):
        print("   npm packages no encontrados")
        print("   Ejecutando 'npm install' en background...")
        print("   (Esto puede tomar varios minutos)")
        
        # Ejecutar npm install sin esperar
        if sys.platform == "win32":
            subprocess.Popen("npm install", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen("npm install", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print("✅ npm install iniciado en background")
    else:
        print("   ✓ npm packages ya están instalados")
        print("✅ Frontend listo")
    
    return True

def verify_setup():
    """Verifica que todo esté listo."""
    print("7️⃣  Verificando setup...")
    
    checks = [
        ("Python 3", "python3 --version"),
        ("Node.js", "node --version"),
        ("npm", "npm --version"),
        ("Git", "git --version"),
    ]
    
    for check_name, cmd in checks:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                print(f"   ✓ {check_name}: {version[:40]}")
            else:
                print(f"   ⚠️  {check_name} - no disponible")
        except Exception as e:
            print(f"   ⚠️  {check_name} - error: {str(e)[:20]}")
    
    print("✅ Verificación completada")

def main():
    """Función principal."""
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  🚀 SETUP COMPLETO - SISTEMA DE INVENTARIO V2.0          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    
    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Ejecutar pasos
    try:
        chmod_scripts()
        print()
        
        clean_venv()
        print()
        
        if not create_venv():
            sys.exit(1)
        print()
        
        if not install_dependencies():
            sys.exit(1)
        print()
        
        if not init_database():
            sys.exit(1)
        print()
        
        if not install_frontend():
            pass  # No es crítico
        print()
        
        verify_setup()
        print()
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelado por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        sys.exit(1)
    
    # Resumen final
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  ✅ SETUP COMPLETADO EXITOSAMENTE                        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("🚀 Ahora ejecuta en 2 terminales separadas:")
    print()
    print("  Terminal 1 (Backend):")
    print("    ./start-backend.sh")
    print()
    print("  Terminal 2 (Frontend):")
    print("    ./start-frontend.sh")
    print()
    print("  Luego abre en navegador:")
    print("    http://localhost:5173")
    print()

if __name__ == "__main__":
    main()
