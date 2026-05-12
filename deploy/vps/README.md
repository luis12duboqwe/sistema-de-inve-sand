# Deploy VPS: invjear.com

Configuracion para desplegar el sistema en un VPS Linux con Nginx y systemd.

## 1. DNS

Crea registros A/AAAA apuntando al IP del VPS:

- `invjear.com`
- `www.invjear.com`

## 2. Paquetes base

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx python3-venv python3-pip postgresql-client git
```

Instala Node.js LTS si el servidor no lo tiene:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

## 3. Usuario y rutas

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin inventario || true
sudo mkdir -p /var/www/inventario /var/backups/inventory /var/log
sudo chown -R inventario:www-data /var/www/inventario /var/backups/inventory
```

Clona o copia el proyecto en `/var/www/inventario`.

## 4. Backend

```bash
cd /var/www/inventario/backend
sudo -u inventario python3 -m venv venv
sudo -u inventario ./venv/bin/pip install -r requirements.txt
sudo -u inventario python3 init_db.py --with-data
```

Configura `/var/www/inventario/backend/.env` con valores reales. Minimo esperado:

```bash
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+psycopg2://USUARIO:PASSWORD@localhost:5432/inventory_db
CORS_ORIGINS=https://invjear.com,https://www.invjear.com
ALLOWED_HOSTS=invjear.com,www.invjear.com,localhost,127.0.0.1
ENABLE_AUTO_BACKUP=true
BACKUP_DIR=/var/backups/inventory
BACKUP_RETENTION_DAYS=30
SENTRY_DISABLED=true
ENABLE_AI_FEATURES=false
```

Genera valores seguros en el VPS:

```bash
openssl rand -hex 32
/var/www/inventario/backend/venv/bin/python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

## 5. Frontend

```bash
cd /var/www/inventario
npm ci
npm run build
sudo chown -R inventario:www-data dist
```

El frontend usa `/api` en produccion, asi que no necesita subdominio de API.

## 6. systemd

```bash
sudo cp /var/www/inventario/deploy/vps/inventario.service /etc/systemd/system/inventario.service
sudo systemctl daemon-reload
sudo systemctl enable --now inventario
sudo systemctl status inventario
```

## 7. Nginx y SSL

Primero activa la configuracion HTTP temporal:

```bash
sudo cp /var/www/inventario/deploy/vps/invjear-nginx-bootstrap.conf /etc/nginx/sites-available/invjear.com
sudo ln -sf /etc/nginx/sites-available/invjear.com /etc/nginx/sites-enabled/invjear.com
sudo nginx -t
sudo systemctl reload nginx
```

Luego emite el certificado:

```bash
sudo certbot --nginx -d invjear.com -d www.invjear.com
```

Finalmente usa la configuracion SSL final:

```bash
sudo cp /var/www/inventario/deploy/vps/invjear-nginx-ssl.conf /etc/nginx/sites-available/invjear.com
sudo nginx -t
sudo systemctl reload nginx
```

## 8. Backups

```bash
sudo cp /var/www/inventario/deploy/vps/inventario-backup.cron /etc/cron.d/inventario-backup
sudo chmod 0644 /etc/cron.d/inventario-backup
sudo -u inventario bash -lc 'cd /var/www/inventario/backend && set -a && . ./.env && set +a && ./backup_database.sh'
```

## 9. Smoke test

```bash
curl -f https://invjear.com/health
curl -f https://invjear.com/api/health
sudo journalctl -u inventario -n 100 --no-pager
```