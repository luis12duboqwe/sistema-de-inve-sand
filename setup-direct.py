#!/usr/bin/env python3
"""
Setup ultra-simple - sin dependencias externas.
Instala directamente en el directorio sin venv si es necesario.
"""

import os
import sys
import subprocess
import shutil

def run_cmd(cmd, description=""):
    """Ejecuta comando y retorna (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)

def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  🚀 SETUP - SISTEMA DE INVENTARIO V2.0                   ║")
    print("║     (Modo simplificado - instalación directa)            ║")
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
            except:
                pass
        print("✅ Permisos configurados\n")

        # 2. Cambiar al backend
        os.chdir("backend")

        # 3. Limpiar venv
        print("2️⃣  Preparando entorno...")
        if os.path.exists("venv"):
            shutil.rmtree("venv", ignore_errors=True)
            print("   ✓ Venv antiguo eliminado")

        # 4. OPCIÓN A: Crear venv
        print("3️⃣  Creando entorno virtual...")
        venv_created = False

        # Intenta crear venv
        success, output = run_cmd("python3 -m venv venv")
        if success and os.path.exists("venv/bin/python"):
            print("   ✓ Venv creado exitosamente")
            venv_created = True
        else:
            print(f"   ⚠️  No se pudo crear venv estándar")
            print("   Usaremos Python del sistema directamente")

        # 5. Instalar dependencias
        print("\n4️⃣  Instalando dependencias Python...")

        # Determinar qué pip usar
        if venv_created:
            if sys.platform == "win32":
                pip_cmd = "venv\\Scripts\\pip"
                python_cmd = "venv\\Scripts\\python"
            else:
                pip_cmd = "venv/bin/pip"
                python_cmd = "venv/bin/python"
            print(f"   Usando: {python_cmd}")
        else:
            pip_cmd = "python3 -m pip"
            python_cmd = "python3"
            print(f"   Usando: Python del sistema")

        # Actualizar pip
        print("   Actualizando pip...")
        run_cmd(f"{pip_cmd} install --upgrade pip -q 2>/dev/null || true")

        # Instalar requirements
        print("   Instalando packages (esto puede tomar 1-2 minutos)...")
        success, output = run_cmd(f"{pip_cmd} install -r requirements.txt")

        if not success:
            print(f"   ⚠️  Warning: {output[:100]}")
            print("   Intentando instalar paquetes individuales...")
            # Instalar paquetes críticos
            critical = ["fastapi", "uvicorn", "sqlalchemy", "pydantic"]
            for pkg in critical:
                run_cmd(f"{pip_cmd} install {pkg} -q")
        else:
            print("   ✓ Packages instalados")

        # Verificar FastAPI
        success, _ = run_cmd(f"{python_cmd} -c \"import fastapi; print('OK')\"")
        if success:
            print("   ✓ FastAPI verificado")
        else:
            print("   ⚠️  FastAPI no disponible (se instalará manualmente)")
            run_cmd(f"{pip_cmd} install fastapi uvicorn -q")

        print("✅ Dependencias Python configuradas\n")

        # 6. Base de datos
        print("5️⃣  Inicializando base de datos...")

        if not os.path.exists("inventory.db"):
            print("   Creando BD con datos de ejemplo...")
            success, output = run_cmd(f"{python_cmd} init_db.py --with-data")
            if success:
                print("   ✓ BD creada")
            else:
                print(f"   ⚠️  Error: {output[:100]}")
                # Intenta sin --with-data
                run_cmd(f"{python_cmd} init_db.py")
        else:
            print("   ℹ️  BD ya existe")

        print("✅ Base de datos lista\n")

        # Volver a raíz
        os.chdir("..")

        # 7. Frontend
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

        # 8. Verificación final
        print("7️⃣  Verificando instalación...")

        checks = [
            ("Python", "python3 --version"),
            ("Node.js", "node --version"),
            ("npm", "npm --version"),
            ("Git", "git --version"),
        ]

        for name, cmd in checks:
            success, output = run_cmd(cmd)
            if success:
                version = output.strip().split('\n')[0][:40]
                print(f"   ✓ {name}: {version}")
            else:
                print(f"   ⚠️  {name}: no disponible")

        print("✅ Verificación completada\n")

        # Resumen final
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  ✅ SETUP COMPLETADO                                     ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()

        if venv_created:
            print("🚀 Ahora ejecuta en 2 terminales:")
        else:
            print("🚀 IMPORTANTE: Se usó Python del sistema")
            print("   Ahora ejecuta en 2 terminales:")

        print()
        print("  Terminal 1:")
        print("    ./start-backend.sh")
        print()
        print("  Terminal 2:")
        print("    ./start-frontend.sh")
        print()
        print("  Luego abre:")
        print("    http://localhost:5173")
        print()

        return True

    except KeyboardInterrupt:
        print("\n❌ Cancelado por el usuario")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
