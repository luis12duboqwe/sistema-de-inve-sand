# Mejoras de Producción - Sistema de Canales

## Sumario

Este documento describe las mejoras de producción implementadas para fortalecer la seguridad, confiabilidad y observabilidad del sistema de integración de canales multi-perfil.

## 1. Cifrado de Tokens (`app/crypto.py`)

### Descripción

Los tokens de acceso y credenciales sensibles se pueden cifrar en la base de datos usando la librería `cryptography.fernet`.

### Cómo usar

#### Generar clave de encriptación

```bash
cd backend
python3 -m app.crypto generate
```

Output:
```
🔑 Nueva clave de encriptación generada:

CHANNEL_ENCRYPTION_KEY=gAAAAABl...zX5Q==

Agregá esto a tu .env y reinicia el servidor.
⚠  Guarda la clave en un lugar seguro (ej: 1Password, HashiCorp Vault)
```

#### Configurar en `.env`

```bash
# .env o docker-compose.prod.yml
CHANNEL_ENCRYPTION_KEY=gAAAAABl...zX5Q==
```

#### Enable cifrado en aplicación

```python
# En routers/channel_integrations.py o donde se guarden tokens
from app.crypto import encrypt_token, decrypt_token, is_encryption_enabled

if is_encryption_enabled():
    profile.access_token = encrypt_token(plaintext_token)
    db.commit()

# Para usar
token = decrypt_token(profile.access_token)  # Devuelve plaintext
api_call(token=token)
```

### Características

- **Fallback seguro**: Si no está configurada `CHANNEL_ENCRYPTION_KEY`, se usa plaintext (dev mode)
- **Migración gradual**: Soporta tokens encriptados y plaintext simultáneamente
- **Fernet (AES)**: Encriptación simétrica con autenticación
- **No reversible manualmente**: Solo la aplicación con la clave puede desencriptar

### Consideraciones de seguridad

1. **Guarda la clave**: Una vez generada, no la pierdas (no hay recuperación posible)
2. **Vault**: Para producción, guarda en HashiCorp Vault, AWS Secrets Manager, o similar
3. **Rotación**: Para rotar claves, necesitas descencriptar todos los tokens con clave old, encriptarlos con clave new
4. **Restricción de acceso**: La BD debe estar protegida (RBAC, firewalls)

## 2. Auditoría y Logging (`app/channel_audit.py`)

### Descripción

Sistema estructurado de event logging para auditar cada acción en canales.

### Uso

```python
from app.channel_audit import (
    log_channel_event,
    log_webhook_received,
    log_config_change,
    log_connection_test,
    channel_metrics,
    ChannelEventType
)

# Registrar evento de mensaje recibido
log_webhook_received(
    channel="whatsapp",
    message_id="wamid_123",
    sales_profile_slug="softmobile-bot",
    customer_id="1234567890",
    customer_name="Juan",
    message_text="Hola, ¿cuánto cuesta el iPhone?"
)

# Registrar cambio de configuración
log_config_change(
    channel="whatsapp",
    event_type=ChannelEventType.CONFIG_UPDATED,
    sales_profile_slug="softmobile-bot",
    changed_fields={"phone_number_id": ("old", "new")},  # No loguear tokens
    changed_by="admin@example.com"
)

# Registrar test de conexión
log_connection_test(
    channel="whatsapp",
    sales_profile_slug="softmobile-bot",
    success=True,
    error=None
)

# Obtener métricas
metrics = channel_metrics.get_summary()
print(metrics)
# Output:
# {
#   "messages_received": {"whatsapp": 42, "messenger": 15, "instagram:softmobile-bot": 8},
#   "messages_sent": {...},
#   "duplicate_messages": {...},
#   "api_errors": {...}
# }
```

### Tipos de eventos auditables

```python
ChannelEventType.MESSAGE_RECEIVED       # Mensaje entrante
ChannelEventType.MESSAGE_SENT           # Respuesta enviada
ChannelEventType.MESSAGE_DUPLICATE      # Deduplicación
ChannelEventType.CONFIG_CREATED         # Nuevo perfil con canal
ChannelEventType.CONFIG_UPDATED         # Actualización de credenciales
ChannelEventType.CONFIG_DELETED         # Eliminación de canal
ChannelEventType.CREDENTIALS_ROTATED    # Cambio de tokens
ChannelEventType.CONNECTION_TESTED      # Test de conexión
ChannelEventType.CONNECTION_SUCCESS     # Test exitoso
ChannelEventType.CONNECTION_FAILED      # Test fallido
ChannelEventType.WEBHOOK_VERIFICATION_FAILED
ChannelEventType.INVALID_SIGNATURE
ChannelEventType.MISSING_CREDENTIALS
ChannelEventType.TOKEN_EXPIRED
ChannelEventType.API_ERROR
ChannelEventType.ROUTING_ERROR
ChannelEventType.PROFILE_ACTIVATED
ChannelEventType.PROFILE_DEACTIVATED
```

### Formato de log

```
[WHATSAPP] message_received | perfil=softmobile-bot | customer=1234567890 | 
details={"message_id": "wamid_123", "customer_name": "Juan", "message_preview": "Hola, ¿cuánto..."}
```

### Niveles de severidad

```python
log_channel_event(..., severity="critical")  # Error grave
log_channel_event(..., severity="error")     # Error
log_channel_event(..., severity="warning")   # Advertencia
log_channel_event(..., severity="info")      # Info (default)
log_channel_event(..., severity="debug")     # Debug
```

### Redacción automática de secretos

Campos con `token`, `password`, `secret`, `key` se redactan automáticamente:

```python
log_config_change(
    ...,
    changed_fields={
        "access_token": ("EAA...old", "EAA...new"),
        "page_id": ("123456", "789012")
    }
)

# Log resultante:
# changed_fields={
#     "access_token": ("***REDACTED***", "***REDACTED***"),
#     "page_id": ("123456", "789012")
# }
```

## 3. Endpointss de Monitoreo (`app/routers/channel_monitoring.py`)

### Endpoints

#### 1. `GET /api/channels/monitoring/metrics`

Retorna métricas en vivo del sistema.

```json
{
  "timestamp": "2024-03-10T15:30:00Z",
  "metrics": {
    "messages_received": {
      "whatsapp": 42,
      "messenger": 15,
      "instagram:softmobile-bot": 8
    },
    "messages_sent": {...},
    "duplicate_messages": {"whatsapp": 2},
    "api_errors": {"messenger": 1}
  }
}
```

#### 2. `GET /api/channels/monitoring/audit/{sales_profile_slug}`

Log de auditoría de un perfil específico.

```bash
GET /api/channels/monitoring/audit/softmobile-bot?hours=24

Response:
{
  "timestamp": "2024-03-10T15:30:00Z",
  "sales_profile_slug": "softmobile-bot",
  "hours_range": 24,
  "interaction_count": 42,
  "recent_interactions": [
    {
      "id": 1,
      "role": "user",
      "content": "Hola, ¿cuál es el precio del iPhone?",
      "tokens_used": 45,
      "created_at": "2024-03-10T15:29:00Z"
    },
    ...
  ],
  "processed_messages_count": 42,
  "processed_messages_by_channel": {
    "whatsapp": {
      "count": 30,
      "recent": [
        {
          "message_id": "wamid_123",
          "customer_phone": "34600000000",
          "processed_at": "2024-03-10T15:29:00Z",
          "expires_at": "2024-03-10T15:40:00Z"
        }
      ]
    },
    "messenger": {...}
  }
}
```

#### 3. `GET /api/channels/monitoring/status`

Estado general del sistema de canales.

```json
{
  "timestamp": "2024-03-10T15:30:00Z",
  "system_status": "operational",
  "profiles_with_channels": 6,
  "profiles": [
    {
      "slug": "softmobile-bot",
      "name": "Softmobile Bot IA",
      "canales": ["whatsapp", "messenger", "instagram"],
      "tipo": "bot_ia"
    },
    {
      "slug": "techstore-vendedor",
      "name": "TechStore Vendedor",
      "canales": ["whatsapp", "facebook"],
      "tipo": "vendedor_humano"
    }
  ],
  "last_24h": {
    "interactions": 312,
    "messages_processed": 547
  },
  "metrics": {...}
}
```

### Parámetros comunes

- `hours`: Para `/audit`, rango en horas (1-168, default 24)
- `profile_slug`: Para `/audit`, slug del perfil

## 4. Deduplicación Persistente

Ver [tarea 2](/#persistencia-de-deduplicación-en-db) arriba.

### Ventajas de persistencia en DB

1. **Cross-restart**: Deduplicación sobrevive reinicios
2. **Distributed**: Si hay múltiples instancias de backend, la deduplicación es compartida
3. **Auditable**: Todos los mensajes procesados quedan registrados
4. **TTL automático**: Limpieza automática de mensajes expirados

### Tabla: `processed_messages`

```sql
CREATE TABLE processed_messages (
  id INTEGER PRIMARY KEY,
  message_id VARCHAR(255) UNIQUE NOT NULL,
  channel VARCHAR(50) NOT NULL,
  customer_phone VARCHAR(50),
  sales_profile_id INTEGER FOREIGN KEY,
  processed_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  
  FOREIGN KEY (sales_profile_id) REFERENCES sales_profiles(id)
)
```

### Migración

```bash
cd backend
python3 migrate_add_deduplication_table.py
```

## 5. Recomendaciones de Seguridad para Producción

### A. Datos en tránsito

- ✅ **HTTPS obligatorio**: Meta requiere HTTPS, así que ya está forzado
- ✅ **TLS 1.2+**: Asegurar configuración en servidor HTTPS (nginx, Cloudflare, etc.)
- ✅ **PIN certificate**: Si es posible, pin el certificado de Meta

### B. Datos en reposo

- ✅ **Encriptación de tokens**: Implementado (opcional en dev, recomendado en prod)
- ✅ **Backup cifrado**: Encriptar backups de BD con claves diferentes
- ✅ **Cumplimiento GDPR/CCPA**: Log retention policies, data deletion requests

### C. Acceso a credenciales

- **Restricción de BD**: 
  - Firewall: Solo aplicación puede acceder
  - RBAC: Usuario BD con permisos mínimos (SELECT, UPDATE en columnas específicas)
  - Auditoría: Log todas las queries a `processed_messages`, `sales_profiles`

- **Restricción de API**:
  - `/api/channels/test-connection` requiere auth
  - `/api/channels/monitoring/*` requiere admin permission
  - No exponer canvas en respuestas públicas

- **Secretos en código**:
  - Nunca hardcodear tokens
  - Usar variables de entorno o vault únicamente
  - Rotar tokens regularmente (90 días recomendado)

### D. Logging seguro

- **No loguear plaintext de tokens** (ya implementado con redacción automática)
- **Retención**: Eliminar logs después de X días (según GDPR requirements)
- **Acceso restringido**: Solo administradores ven logs sensibles

### E. Monitoreo y alertas

Implementar alertas para:
- Múltiples errores de API en corto plazo → Token expirado probable
- Cambios de credenciales → Auditoría requerida
- Webhook failures → Webhook URL o verify token incorrecto
- Duplicate message spike → Posible loop o replay attack

### F. Mejoras futuras

```
- [ ] Rotate Fernet encryption key (zero-downtime)
- [ ] Webhook signature time validation (evitar replay)
- [ ] Rate limiting por customer phone
- [ ] IP whitelist para incoming webhooks
- [ ] 2FA para cambios de credenciales
- [ ] Monthly token rotation automation
- [ ] Compliance reports (GDPR SAR, CCPA)
```

## 6. Troubleshooting de Producción

### Problema: "Token encriptado se está guardando como plaintext"

**Causa**: `CHANNEL_ENCRYPTION_KEY` no configurado

**Solución**:
```bash
# 1. Generar clave
python3 -m app.crypto generate

# 2. Agregar a .env
echo "CHANNEL_ENCRYPTION_KEY=..." >> .env

# 3. Reiniciar backend
docker-compose restart backend
```

### Problema: "No puedo desencriptar tokens después de reiniciar"

**Causa**: `CHANNEL_ENCRYPTION_KEY` cambió (diferente en `.env`)

**Solución**:
```bash
# 1. Restaurar la clave original de .env
# 2. Confirmar con: python -c "from app.crypto import _crypto_manager; print(_crypto_manager.is_encrypted_mode())"
```

### Problema: "Logs gigantes por audit logging"

**Mitigation**:
```python
# En config.py
CHANNEL_AUDIT_LOG_LEVEL = "warning"  # Solo warnings, errors, critically
# o
CHANNEL_AUDIT_DISABLED = False  # Desabilitar auditoria
```

### Problema: "Tabla processed_messages creció mucho"

**Causa**: Muchos mensajes sin cleanup

**Solución**:
```sql
-- Limpiar mensajes expirados manualmente
DELETE FROM processed_messages WHERE expires_at < NOW();

-- Index para acelerar queries
CREATE INDEX idx_processed_message_channel_profile ON processed_messages(channel, sales_profile_id);
```

## 7. Performance

### Optimizaciones ya implementadas

- ✅ Índices en `processed_messages` para cleanup automático
- ✅ Deduplicación O(1) usando message_id único
- ✅ Lazy loading de configuración (no precarga todos los tokens)
- ✅ Async channel replies (no bloquea webhook)

### Recomendaciones futuras

- **Redis deduplication**: Si llegan >1000 mensajes/minuto, usar Redis para cache hot
- **Async logging**: Usar queue para no bloquear handler con logs
- **Batch cleanup**: Limpiar processed_messages cada 1h en lugar de por request

## 8. Archivos creados/modificados

### Nuevos

- `backend/app/crypto.py` - Cifrado de tokens
- `backend/app/channel_audit.py` - Auditoría y logging
- `backend/app/routers/channel_monitoring.py` - Endpoints de monitoreo
- `backend/migrate_add_deduplication_table.py` - Migración de tabla

### Modificados

- `backend/app/main.py` - Agregar router de monitoring
- `backend/app/models/ai.py` - Agregar modelo ProcessedMessage
- `backend/app/routers/channel_integrations.py` - Usar deduplicación en DB
- `backend/app/database.py` - Asegurar índices en ProcessedMessage

## 9. Pasos de deployment

### Pre-flight checklist

- [ ] Generar `CHANNEL_ENCRYPTION_KEY`
- [ ] Configurar en `.env` o secret manager
- [ ] Ejecutar migración: `python migrate_add_deduplication_table.py`
- [ ] Probar endpoints de monitoreo en staging
- [ ] Revisar logs y métricas
- [ ] Implementar alertas en monitoring (Datadog, New Relic, etc.)

### Deployment

```bash
# 1. Migrar BD
python backend/migrate_add_deduplication_table.py

# 2. Redeploy aplicación
docker-compose -f docker-compose.prod.yml up -d

# 3. Verificar
curl -H "Authorization: Bearer <token>" https://yourdomain.com/api/channels/monitoring/status

# 4. Monitorear
tail -f logs/channels.log | grep -i error
```

---

**Versión**: 2.0  
**Fecha**: March 10, 2026  
**Última revisión**: Production-ready
