# ⚙️ Configuración de Permisos

Si ves el error `Permission denied` al ejecutar los scripts, es porque necesitan permisos de ejecución.

## Solución Rápida

### Opción 1: Usar Python (más seguro)
```bash
python3 fix_permissions.py
```

### Opción 2: Usar bash
```bash
bash fix-permissions.sh
```

### Opción 3: Manual con chmod
```bash
chmod +x start-backend.sh
chmod +x start-frontend.sh
chmod +x setup-backend.sh
chmod +x test-system.sh
chmod +x backend/start.sh
```

## Luego Puedes Iniciar

```bash
# Terminal 1 - Backend
./start-backend.sh

# Terminal 2 - Frontend
./start-frontend.sh
```

## ¿Por qué sucede esto?

Cuando se clonan los archivos de git en algunos sistemas (especialmente en dev containers), los permisos de ejecución no se preservan correctamente. Esto es especialmente común en:

- **Dev Containers** de VS Code
- **WSL** (Windows Subsystem for Linux)
- **Archivos descargados** desde el navegador
- **Repositorios clonados** con ciertas configuraciones de git

## Verificar Permisos

Para ver si los scripts ya son ejecutables:

```bash
ls -la start-backend.sh
# Si es ejecutable verás una "x": -rwxr-xr-x
# Si no es ejecutable verás: -rw-r--r--
```

---

**Nota**: Esta es una configuración única. Una vez hecho, no necesitarás hacerlo de nuevo. 🚀
