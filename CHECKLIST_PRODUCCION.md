# Checklist de Preparación para Producción

Este checklist ayuda a verificar que el sistema está listo para ser desplegado en producción de forma segura.

---

## 📋 Pre-Deployment Checklist

### 1. Configuración de Entorno

- [ ] Copiar `.env.production.example` a `.env`
  ```bash
  cd backend
  cp .env.production.example .env
  ```

- [ ] Editar `.env` con valores reales:
  - [ ] `SECRET_KEY` - Generar con `openssl rand -hex 32`
  - [ ] `DATABASE_URL` - PostgreSQL o MySQL (no SQLite)
  - [ ] `CORS_ORIGINS` - Solo dominios autorizados (no `*`)
  - [ ] `DEBUG=false`
  - [ ] `ENVIRONMENT=production`

- [ ] Configurar email (SMTP):
  - [ ] `SMTP_HOST`
  - [ ] `SMTP_USER`
  - [ ] `SMTP_PASSWORD`
  - [ ] `SMTP_FROM`

- [ ] (Opcional) Configurar OpenAI si se usa IA:
  - [ ] `OPENAI_API_KEY`
  - [ ] `ENABLE_AI_FEATURES=true`

- [ ] (Opcional) Configurar N8N/WhatsApp:
  - [ ] `N8N_WEBHOOK_URL`
  - [ ] `N8N_AUTH_TOKEN`

### 2. Base de Datos

- [ ] Migrar de SQLite a PostgreSQL/MySQL
  ```bash
  # Exportar datos de SQLite
  python backend/export_data.py  # Crear este script si no existe
  
  # Configurar PostgreSQL
  # DATABASE_URL=postgresql://user:pass@localhost:5432/inventario
  
  # Importar datos
  python backend/init_db.py --import
  ```

- [ ] Verificar conexión a BD
  ```bash
  cd backend
  python check_production_readiness.py
  ```

- [ ] Crear backup inicial
  ```bash
  pg_dump -U usuario inventario > backup_inicial.sql
  ```

- [ ] Configurar backups automáticos:
  - [ ] `ENABLE_AUTO_BACKUP=true`
  - [ ] `BACKUP_DIR=/var/backups/inventario`
  - [ ] `BACKUP_RETENTION_DAYS=30`

### 3. Seguridad

- [ ] Verificar SECRET_KEY no es valor por defecto
- [ ] Verificar CORS restringido (no `*`)
- [ ] Verificar DEBUG=false
- [ ] Configurar rate limiting:
  - [ ] `RATE_LIMIT_PER_MINUTE=100`
  - [ ] `LOGIN_ATTEMPTS_LIMIT=5`

- [ ] Crear usuario administrador
  ```bash
  cd backend
  python reset_admin.py  # Cambiar contraseña por defecto
  ```

- [ ] Verificar permisos de archivos
  ```bash
  chmod 600 backend/.env  # Solo owner puede leer
  chmod 700 backend/logs  # Solo owner puede escribir
  ```

### 4. Logging y Monitoreo

- [ ] Configurar directorio de logs:
  - [ ] `LOG_DIR=/var/log/inventario`
  - [ ] Crear directorio: `sudo mkdir -p /var/log/inventario`
  - [ ] Permisos: `sudo chown $USER:$USER /var/log/inventario`

- [ ] Habilitar logging a archivos:
  - [ ] `ENABLE_FILE_LOGGING=true`
  - [ ] `LOG_LEVEL=INFO` (no DEBUG en producción)
  - [ ] `LOG_FORMAT=json`

- [ ] (Opcional) Configurar Sentry:
  - [ ] `SENTRY_DSN=https://...`

- [ ] (Opcional) Configurar New Relic:
  - [ ] `NEW_RELIC_LICENSE_KEY=...`

### 5. Testing

- [ ] Ejecutar tests del backend
  ```bash
  cd backend
  python -m pytest tests/ -v
  ```

- [ ] Testing manual de flujos críticos:
  - [ ] Crear producto
  - [ ] Crear orden (con stock suficiente)
  - [ ] Crear orden (con stock insuficiente - debe fallar)
  - [ ] Transferencia de stock
  - [ ] Cancelar orden (debe devolver stock)
  - [ ] Exportar orden a PDF/HTML
  - [ ] Login/logout
  - [ ] Cambiar contraseña

- [ ] Verificar que sistema pasa check de producción
  ```bash
  cd backend
  python check_production_readiness.py
  # Debe mostrar: "✓ SISTEMA LISTO PARA PRODUCCIÓN"
  ```

### 6. Servidor Web (Nginx/Apache)

- [ ] Instalar Nginx
  ```bash
  sudo apt update
  sudo apt install nginx
  ```

- [ ] Configurar reverse proxy
  ```nginx
  # /etc/nginx/sites-available/inventario
  server {
      listen 80;
      server_name tu-dominio.com;
      
      location / {
          proxy_pass http://localhost:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
      
      location /static {
          alias /var/www/inventario/static;
      }
  }
  ```

- [ ] Habilitar sitio
  ```bash
  sudo ln -s /etc/nginx/sites-available/inventario /etc/nginx/sites-enabled/
  sudo nginx -t
  sudo systemctl reload nginx
  ```

### 7. SSL/TLS (HTTPS)

- [ ] Instalar Certbot
  ```bash
  sudo apt install certbot python3-certbot-nginx
  ```

- [ ] Obtener certificado SSL
  ```bash
  sudo certbot --nginx -d tu-dominio.com
  ```

- [ ] Verificar auto-renovación
  ```bash
  sudo certbot renew --dry-run
  ```

### 8. Systemd Service (Auto-inicio)

- [ ] Crear service file
  ```ini
  # /etc/systemd/system/inventario.service
  [Unit]
  Description=Sistema de Inventario API
  After=network.target postgresql.service
  
  [Service]
  Type=simple
  User=www-data
  Group=www-data
  WorkingDirectory=/var/www/inventario/backend
  Environment="PATH=/var/www/inventario/backend/venv/bin"
  ExecStart=/var/www/inventario/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  Restart=always
  RestartSec=10
  
  [Install]
  WantedBy=multi-user.target
  ```

- [ ] Habilitar y iniciar servicio
  ```bash
  sudo systemctl enable inventario
  sudo systemctl start inventario
  sudo systemctl status inventario
  ```

### 9. Backups Automáticos

- [ ] Crear script de backup
  ```bash
  # /usr/local/bin/backup-inventario.sh
  #!/bin/bash
  BACKUP_DIR=/var/backups/inventario
  DATE=$(date +%Y%m%d_%H%M%S)
  
  # Backup de BD
  pg_dump -U inventario_user inventario > $BACKUP_DIR/db_$DATE.sql
  
  # Backup de archivos
  tar -czf $BACKUP_DIR/files_$DATE.tar.gz /var/www/inventario
  
  # Limpiar backups antiguos (más de 30 días)
  find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
  find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
  ```

- [ ] Hacer ejecutable
  ```bash
  sudo chmod +x /usr/local/bin/backup-inventario.sh
  ```

- [ ] Configurar cron job
  ```bash
  sudo crontab -e
  # Agregar línea:
  0 2 * * * /usr/local/bin/backup-inventario.sh
  ```

### 10. Monitoreo y Alertas

- [ ] Configurar log rotation
  ```bash
  # /etc/logrotate.d/inventario
  /var/log/inventario/*.log {
      daily
      rotate 30
      compress
      delaycompress
      notifempty
      create 0640 www-data www-data
      sharedscripts
      postrotate
          systemctl reload inventario
      endscript
  }
  ```

- [ ] (Opcional) Configurar alertas de errores
  - [ ] Email on critical errors
  - [ ] Slack/Discord webhooks
  - [ ] SMS para errores críticos

### 11. Documentación

- [ ] Actualizar README con:
  - [ ] URL de producción
  - [ ] Credenciales de acceso (usuario admin)
  - [ ] Contactos de soporte

- [ ] Crear runbook para operaciones comunes:
  - [ ] Reiniciar servicio
  - [ ] Restaurar backup
  - [ ] Ver logs de errores
  - [ ] Agregar nuevo usuario

### 12. Verificación Final

- [ ] Acceder a sistema vía HTTPS
- [ ] Login con usuario administrador
- [ ] Crear orden de prueba
- [ ] Exportar reporte
- [ ] Verificar logs en `/var/log/inventario/`
- [ ] Simular error (verificar logging)
- [ ] Verificar backup automático se ejecuta

---

## 🚀 Deployment

### Pasos Finales

1. **Ejecutar verificación completa**
   ```bash
   cd backend
   python check_production_readiness.py
   ```

2. **Iniciar sistema**
   ```bash
   sudo systemctl start inventario
   sudo systemctl status inventario
   ```

3. **Monitorear logs iniciales**
   ```bash
   tail -f /var/log/inventario/app.log
   ```

4. **Verificar salud del sistema**
   ```bash
   curl https://tu-dominio.com/api/health
   ```

---

## 🆘 Rollback Plan

Si algo sale mal durante el deployment:

### Paso 1: Detener servicio nuevo
```bash
sudo systemctl stop inventario
```

### Paso 2: Restaurar backup de BD
```bash
psql -U inventario_user inventario < /var/backups/inventario/db_YYYYMMDD_HHMMSS.sql
```

### Paso 3: Restaurar código anterior
```bash
cd /var/www/inventario
git checkout <tag_version_anterior>
```

### Paso 4: Reiniciar con configuración anterior
```bash
sudo systemctl start inventario
```

---

## 📊 Post-Deployment

### Primeras 24 horas
- [ ] Monitorear logs cada 2 horas
- [ ] Verificar backups se ejecutan correctamente
- [ ] Verificar performance (tiempos de respuesta)
- [ ] Verificar que no hay errores críticos

### Primera semana
- [ ] Revisar logs de errores diariamente
- [ ] Verificar uso de recursos (CPU, memoria, disco)
- [ ] Ajustar workers de Uvicorn si es necesario
- [ ] Optimizar queries lentas (si aplica)

### Primer mes
- [ ] Revisar métricas de uso
- [ ] Ajustar backups según necesidad
- [ ] Planear optimizaciones basadas en uso real

---

## 📞 Contactos de Emergencia

| Rol | Nombre | Contacto |
|-----|--------|----------|
| Administrador de Sistema | ? | ? |
| DBA | ? | ? |
| Desarrollador Backend | ? | ? |
| Soporte Técnico | ? | ? |

---

## 📚 Referencias

- **Arquitectura**: `docs/ARQUITECTURA.md`
- **Estado de IA**: `docs/ESTADO_IA.md`
- **Guía de Refactorización**: `docs/GUIA_REFACTORIZACION.md`
- **Testing**: `TESTING_GUIDE.md`
- **Configuración de Producción**: `backend/.env.production.example`

---

**Última actualización**: Diciembre 26, 2024

**Estado del Sistema**: 
- ✅ Código listo para producción
- ⚠️ Requiere configuración de `.env`
- ⚠️ Requiere migración de BD a PostgreSQL
- ⚠️ Requiere configuración de servidor web

**Completado**: _____ de 67 items del checklist
