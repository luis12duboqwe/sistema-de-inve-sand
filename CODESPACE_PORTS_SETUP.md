# 🔧 Configuración de Puertos en GitHub Codespaces

## Problema Detectado

Estás en un **GitHub Codespace** y el puerto 8000 (backend) necesita ser **público** para que el frontend pueda conectarse.

## ✅ Solución Rápida (3 pasos)

### 1. Abre la Pestaña PORTS

En VS Code, busca el panel inferior y haz click en la pestaña **"PORTS"** (Puertos)

```
[TERMINAL] [PORTS] [PROBLEMS] [OUTPUT] [DEBUG CONSOLE]
            ^^^^^^
          Click aquí
```

### 2. Encuentra el Puerto 8000

En la lista de puertos, busca el puerto **8000** donde está corriendo el backend.

Si no aparece, primero inicia el backend:
```bash
bash /workspaces/spark-template/run-backend-direct.sh
```

### 3. Cambia la Visibilidad a Public

1. **Click derecho** en el puerto 8000
2. Selecciona **"Port Visibility"**
3. Selecciona **"Public"**

```
Puerto 8000
  ├─ Forward Port
  ├─ Port Visibility  ← Click aquí
  │   ├─ Private
  │   └─ Public      ← Selecciona esto
  └─ Stop Forwarding
```

### 4. Recarga el Frontend

Una vez que el puerto sea público:
- Recarga la página del frontend
- O haz click en "Reintentar Conexión"

## 🔍 Verificación

Después de hacer el puerto público, la URL del backend debería ser:
```
https://bookish-train-4jrwg4r4xj67cjp6-8000.app.github.dev/api
```

Puedes probarla directamente en tu navegador agregando `/profiles` al final:
```
https://bookish-train-4jrwg4r4xj67cjp6-8000.app.github.dev/api/profiles
```

Deberías ver una respuesta JSON como:
```json
{"items":[],"total":0,"page":1,"per_page":50,"pages":0}
```

## 🚨 Alternativa: Comando CLI

Si tienes GitHub CLI instalado:

```bash
gh codespace ports visibility 8000:public -c "$CODESPACE_NAME"
```

## 📝 Notas Importantes

- **Solo necesitas hacer esto una vez** por Codespace
- El puerto se mantendrá público mientras el Codespace esté activo
- Si recreas el Codespace, tendrás que repetir el proceso

## ❓ Problemas?

Si después de hacer el puerto público sigue sin funcionar:

1. Verifica que el backend esté corriendo:
   ```bash
   ps aux | grep uvicorn
   ```

2. Prueba la conexión local:
   ```bash
   curl http://localhost:8000/api/profiles
   ```

3. Revisa los logs del backend en la terminal donde lo iniciaste

4. Usa el botón "Continuar sin conexión (Debug)" temporalmente mientras investigas
