#!/usr/bin/env python3
"""
Script para configurar permisos de ejecución en los scripts shell.
Útil cuando chmod desde bash no funciona correctamente.
"""

import os
import stat
import sys

def make_executable(filepath):
    """Hacer un archivo ejecutable."""
    try:
        st = os.stat(filepath)
        os.chmod(filepath, st.st_mode | stat.S_IEXEC | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"✅ {os.path.basename(filepath)}")
        return True
    except FileNotFoundError:
        print(f"⚠️  {os.path.basename(filepath)} no encontrado")
        return False
    except Exception as e:
        print(f"❌ Error en {os.path.basename(filepath)}: {e}")
        return False

if __name__ == "__main__":
    print("🔐 Configurando permisos de ejecución...")
    print("")
    
    scripts = [
        "./start-backend.sh",
        "./start-frontend.sh",
        "./setup-backend.sh",
        "./test-system.sh",
        "./backend/start.sh",
    ]
    
    success = 0
    for script in scripts:
        if make_executable(script):
            success += 1
    
    print("")
    print(f"✅ {success}/{len(scripts)} scripts configurados")
    print("")
    print("Ahora puedes ejecutar:")
    print("  ./start-backend.sh   - Iniciar el backend")
    print("  ./start-frontend.sh  - Iniciar el frontend")
    print("  ./test-system.sh     - Probar el sistema")
