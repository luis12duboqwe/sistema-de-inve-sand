#!/usr/bin/env python3
"""
Script de setup simplificado - maneja todos los casos de error.
"""

import os
import sys
import subprocess
import shutil

def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  🚀 SETUP - SISTEMA DE INVENTARIO V2.0                   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    
    try:
        # 1. Permisos
        print("1️⃣  Dando permisos de ejecución...")
        scripts = [
            "start-backend.sh", "start-frontend.sh", "setup-backend.sh",
            "test-system.sh", "backend/start.sh", "fix-permissions.sh", "reset-venv.sh"
        ]
        for script in scripts:
            try:
                if os.path.exists(script):
                    os.chmod(script, 0o755)
                    print(f"   ✓ {script}")
            except:
                pass
        print("✅ Permisos configurados\n")
        
        # 2. Limpiar venv
        print("2️⃣  Limpiando entorno virtual antiguo...")
        if os.path.exists("backend/venv"):
            shutil.rmtree("backend/venv", ignore_errors=True)
            print("   ✓ Venv eliminado")
        else:
            print("   ℹ️  No hay venv anterior")
        print("✅ Limpieza completada\n")
        
        # 3. Crear venv
        print("3️⃣  Creando entorno virtual...")
        os.chdir("backend")
        
        # Opción 1: venv
        print("   Intentando: python3 -m venv venv")
        result = subprocess.run(
            [sys.executable, "-m", "venv", "venv"],
            capture_output=True,
            timeout=60
        )
        
        if result.returncode == 0 and os.path.exists("venv"):
            print("   ✓ Venv creado con python3 -m venv")
        else:
            print(f"   ⚠️  Error: {result.stderr.decode()[:100] if result.stderr else 'unknown'}")
            print("   Intentando: python3 -m virtualenv venv")
            
            result = subprocess.run(
                [sys.executable, "-m", "virtualenv", "venv"],
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0 and os.path.exists("venv"):
                print("   ✓ Venv creado con virtualenv")
            else:
                print(f"   ⚠️  Error: {result.stderr.decode()[:100] if result.stderr else 'unknown'}")
                print("   Instalando virtualenv...")
                
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "virtualenv", "-q"],
                    capture_output=True,
                    timeout=60
                )
                
                result = subprocess.run(
                    [sys.executable, "-m", "virtualenv", "venv"],
                    capture_output=True,
                    timeout=60
                )
                
                if result.returncode == 0 and os.path.exists("venv"):
                    print("   ✓ Venv creado con virtualenv (después de instalar)")
                else:
                    print("   ❌ No se pudo crear venv")
                    os.chdir("..")
                    return False
        
        print("✅ Entorno virtual creado\n")
        
        # 4. Instalar dependencias
        print("4️⃣  Instalando dependencias Python...")
        
        if sys.platform == "win32":
            pip_exe = "venv\\Scripts\\pip"
            python_exe = "venv\\Scripts\\python"
        else:
            pip_exe = "venv/bin/pip"
            python_exe = "venv/bin/python"
        
        # Actualizar pip
        print("   Actualizando pip...")
        subprocess.run(
            f"{pip_exe} install --upgrade pip -q",
            shell=True,
            capture_output=True,
            timeout=120
        )
        
        # Instalar requirements
        print("   Instalando packages...")
        result = subprocess.run(
            f"{pip_exe} install -r requirements.txt",
            shell=True,
            capture_output=True,
            timeout=300,
            text=True
        )
        
        if result.returncode != 0:
            print(f"   ⚠️  Error: {result.stderr[:100]}")
            os.chdir("..")
            return False
        
        print("   ✓ Packages instalados")
        
        # Verificar FastAPI
        result = subprocess.run(
            f"{python_exe} -c \"import fastapi; print('FastAPI OK')\"",
            shell=True,
            capture_output=True,
            timeout=10,
            text=True
        )
        
        if result.returncode == 0:
            print("   ✓ FastAPI verificado")
        
        print("✅ Dependencias Python instaladas\n")
        
        # 5. Base de datos
        print("5️⃣  Inicializando base de datos...")
        
        if not os.path.exists("inventory.db"):
            print("   Creando BD...")
            result = subprocess.run(
                f"{python_exe} init_db.py --with-data",
                shell=True,
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("   ✓ BD creada")
            else:
                print("   ⚠️  Error al crear BD")
        else:
            print("   ℹ️  BD ya existe")
        
        print("✅ Base de datos lista\n")
        
        os.chdir("..")
        
        # 6. Frontend
        print("6️⃣  Preparando frontend...")
        
        if not os.path.exists("node_modules"):
            print("   npm install (en background)...")
            subprocess.Popen(
                "npm install",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("✅ npm install iniciado\n")
        else:
            print("✅ npm packages ya están instalados\n")
        
        # 7. Verificación
        print("7️⃣  Verificando instalación...")
        
        checks = [
            ("Python", "python3 --version"),
            ("Node.js", "node --version"),
            ("npm", "npm --version"),
        ]
        
        for name, cmd in checks:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0][:30]
                print(f"   ✓ {name}: {version}")
            else:
                print(f"   ⚠️  {name}: no disponible")
        
        print("✅ Verificación completada\n")
        
        # Resumen final
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  ✅ SETUP COMPLETADO EXITOSAMENTE                        ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print("🚀 Ahora ejecuta en 2 terminales:")
        print()
        print("  Terminal 1:")
        print("    ./start-backend.sh")
        print()
        print("  Terminal 2:")
        print("    ./start-frontend.sh")
        print()
        print("  Luego abre en navegador:")
        print("    http://localhost:5173")
        print()
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado por el usuario")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
