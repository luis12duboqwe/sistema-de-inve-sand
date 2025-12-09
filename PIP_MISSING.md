# ⚠️ Problema: pip no instalado

## Síntoma
```
/usr/bin/python3: No module named pip
```

## Causa
En este Codespace, Python 3 está instalado pero **pip no está disponible por defecto**.

## Solución

### Opción A: Instalar pip automáticamente
```bash
bash install-pip.sh
```

Este script intentará:
1. `python3 -m ensurepip` (método integrado)
2. `apt-get install python3-pip` (si está disponible apt)
3. `yum install python3-pip` (si está disponible yum)

### Opción B: Instalar pip manualmente

#### En Linux (Debian/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install python3-pip
```

#### En Linux (RedHat/CentOS)
```bash
sudo yum install python3-pip
```

#### En macOS
```bash
brew install python3
# o
python3 -m ensurepip --upgrade
```

#### En Windows
Descarga Python 3.11+ desde https://python.org (incluye pip)

### Opción C: Usar ensurepip (Sin sudo)
```bash
python3 -m ensurepip --upgrade
```

## Verificar que pip está instalado
```bash
python3 -m pip --version
# Debería mostrar: pip X.X.X from ...
```

## Después de instalar pip

### Opción 1: Ejecutar setup nuevamente
```bash
bash setup.sh
```

### Opción 2: Instalar dependencias manualmente
```bash
cd backend
python3 -m pip install -r requirements.txt
python3 init_db.py --with-data
cd ..
npm install
```

### Opción 3: Iniciar backend
```bash
./start-backend.sh
```

---

## ¿Por qué falta pip?

En algunos entornos Codespace, Python se instala sin pip por defecto. Esto es raro pero sucede.

**Solución permanente:** Una vez que instales pip, no necesitarás hacerlo de nuevo.

---

## Scripts Actualizados

He actualizado los scripts para **detectar automáticamente** si pip está faltando:

- ✅ `setup.sh` - Intenta instalar pip si no existe
- ✅ `start-backend.sh` - Intenta instalar pip si no existe
- ✅ `install-pip.sh` - Script dedicado solo para instalar pip

---

## Próximo Paso

1. Ejecuta: `bash install-pip.sh`
2. Luego: `bash setup.sh`
3. Luego: `./start-backend.sh` (Terminal 1)
4. Luego: `./start-frontend.sh` (Terminal 2)
