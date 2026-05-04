# Tareas Pendientes: Sistema de Solicitudes de Fotos

## Resumen de estatus

✅ **COMPLETADO** (6/10):
- Modelos de BD: PhotoRequest, PhotoRequestMediaItem
- Schemas Pydantic: Create, Update, Response
- Router API con 6 endpoints
- Utilidades de detección (20+ patrones)
- Dashboard UI (componente React)
- Integración en main.py

❌ **PENDIENTE** (4/10):
- [ ] Integración en prompt AI (detección + respuesta)
- [ ] Implementar send_photos_to_customer() real
- [ ] Implementar _notify_agent_of_request() real
- [ ] Wiring frontend (API client methods)

---

## Task 1: Integración en AI Bot (CRÍTICO)

**Archivo**: `backend/app/routers/ai_intelligence.py`
**Función**: `handle_message_without_n8n()`

**Lo que falta**:
```python
# En handle_message_without_n8n(), agregar ANTES de llamar a GPT-4:

from app.utils.photo_detection import detect_photo_request, extract_photo_request_context, get_response_for_photo_request
from app.schemas.photos import PhotoRequestCreate
import httpx

# ... código existente ...

# NUEVO: Detectar solicitud de fotos
if detect_photo_request(customer_message):
    color, size = extract_photo_request_context(customer_message)
    
    # TODO: Mejorar extracción de nombre de producto
    # Por ahora, asumir el producto más popular o último consultado
    product_name = extract_product_name_from_message(customer_message)
    
    # Crear solicitud
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.API_URL}/api/photo-requests/create",
                json={
                    "customer_id": customer_phone,
                    "product_name": product_name or "Producto",
                    "color_requested": color,
                    "size_requested": size,
                    "additional_notes": customer_message
                },
                params={
                    "sales_profile_slug": sales_profile.slug,
                    "channel": channel,
                    "customer_name": customer_name
                },
                timeout=5
            )
            photo_request_id = response.json().get("id")
            logger.info(f"📸 Photo request created: {photo_request_id} for {customer_phone}")
    except Exception as e:
        logger.error(f"Error creating photo request: {e}")
    
    # Respuesta al cliente (no espera fotos, respuesta inmediata)
    bot_response = get_response_for_photo_request(language="es")
    # "Dame un momento, estoy tomando fotos..."
    
    # NO LLAMAR A GPT-4 en este caso
else:
    # Procesamiento normal: llamar a GPT-4
    bot_response = await call_gpt4(...)

# ... resto del código para enviar respuesta ...
```

**Checklist**:
- [ ] Importar `detect_photo_request`, `extract_photo_request_context`, `get_response_for_photo_request`
- [ ] Importar `PhotoRequestCreate` schema
- [ ] Agregar bloque de detección ANTES de GPT-4
- [ ] Implementar `extract_product_name_from_message()` helper
- [ ] Usar `get_response_for_photo_request()` para respuesta predefinida
- [ ] Agregar logging
- [ ] Probar con mensaje "Quiero ver fotos del iPhone 15 en gris"
- [ ] Verificar que se crea PhotoRequest en BD

---

## Task 2: Enviar Fotos al Cliente (CRÍTICO)

**Archivo**: `backend/app/routers/photo_requests.py`
**Función**: `send_photos_to_customer()` (línea ~280)

**Código actual** (PLACEHOLDER):
```python
@router.post("/{photo_request_id}/send-to-customer")
async def send_photos_to_customer(
    photo_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("photo_requests:send"))
):
    """Send all uploaded photos to customer via original channel."""
    
    photo_request = db.query(PhotoRequest).filter(PhotoRequest.id == photo_request_id).first()
    if not photo_request:
        raise HTTPException(status_code=404, detail="Photo request not found")
    
    # TODO: Get all unset media items
    # TODO: Get sales_profile
    # TODO: Get channel
    # TODO: Send to customer via WhatsApp/Messenger/Instagram
    # TODO: Mark sent_to_customer_at
    # TODO: Mark status=completed
```

**Lo que hay que implementar**:
```python
@router.post("/{photo_request_id}/send-to-customer")
async def send_photos_to_customer(
    photo_request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("photo_requests:send"))
):
    """Send all uploaded photos to customer via original channel."""
    
    photo_request = db.query(PhotoRequest).filter(
        PhotoRequest.id == photo_request_id
    ).first()
    if not photo_request:
        raise HTTPException(status_code=404, detail="Photo request not found")
    
    # 1. Obtener fotos no enviadas
    media_items = db.query(PhotoRequestMediaItem).filter(
        PhotoRequestMediaItem.photo_request_id == photo_request_id,
        PhotoRequestMediaItem.sent_to_customer_at == None
    ).all()
    
    if not media_items:
        raise HTTPException(status_code=400, detail="No media items to send")
    
    # 2. Obtener sales_profile para saber qué canales maneja
    # TODO: Cómo saber de qué sales_profile fue la solicitud?
    # Opción A: Agregar sales_profile_id a PhotoRequest (mejor)
    # Opción B: Obtener del customer_id (requiere tabla customer_sales_profile)
    # Por ahora, asumir que está en sales_profile más reciente del cliente
    
    sales_profiles = db.query(SalesProfile).filter(
        SalesProfile.channels.contains(photo_request.channel)  # TODO: channel field
    ).all()
    
    if not sales_profiles:
        raise HTTPException(status_code=400, detail="No sales profile found for channel")
    
    sales_profile = sales_profiles[0]  # TODO: Elegir mejor
    
    # 3. Enviar fotos por el canal original
    try:
        if photo_request.channel == "whatsapp":
            await send_whatsapp_media(
                phone=photo_request.customer_id,
                media_urls=[item.media_url for item in media_items],
                sales_profile=sales_profile
            )
        elif photo_request.channel == "messenger":
            await send_messenger_media(
                customer_id=photo_request.customer_id,
                media_urls=[item.media_url for item in media_items],
                sales_profile=sales_profile
            )
        elif photo_request.channel == "instagram":
            await send_instagram_media(
                customer_id=photo_request.customer_id,
                media_urls=[item.media_url for item in media_items],
                sales_profile=sales_profile
            )
    except Exception as e:
        logger.error(f"Error sending photos: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending photos: {str(e)}")
    
    # 4. Marcar como enviadas
    from datetime import datetime
    for item in media_items:
        item.sent_to_customer_at = datetime.utcnow()
    
    # 5. Marcar solicitud como completada
    photo_request.status = "completed"
    photo_request.resolved_at = datetime.utcnow()
    
    db.commit()
    
    return _serialize_photo_request(photo_request)
```

**Helpers necesarios** (reutilizar de `channel_integrations.py`):
```python
async def send_whatsapp_media(phone: str, media_urls: list[str], sales_profile: SalesProfile):
    """Send media to WhatsApp customer"""
    from app.services.channel_integrations import WhatsAppIntegration
    
    async with WhatsAppIntegration(sales_profile) as wa:
        for media_url in media_urls:
            await wa.send_media(phone, media_url)

async def send_messenger_media(customer_id: str, media_urls: list[str], sales_profile: SalesProfile):
    """Send media to Messenger customer"""
    from app.services.channel_integrations import MessengerIntegration
    
    async with MessengerIntegration(sales_profile) as messenger:
        for media_url in media_urls:
            await messenger.send_media(customer_id, media_url)

async def send_instagram_media(customer_id: str, media_urls: list[str], sales_profile: SalesProfile):
    """Send media to Instagram customer"""
    from app.services.channel_integrations import InstagramIntegration
    
    async with InstagramIntegration(sales_profile) as ig:
        for media_url in media_urls:
            await ig.send_media(customer_id, media_url)
```

**Checklist**:
- [ ] Obtener media_items no enviadas
- [ ] Obtener sales_profile correcto (MEJORA: agregar sales_profile_id a PhotoRequest)
- [ ] Detectar canal (whatsapp, messenger, instagram)
- [ ] Llamar integradores de canal correspondiente
- [ ] Marcar media.sent_to_customer_at
- [ ] Marcar photo_request.status = completed
- [ ] Manejo de errores
- [ ] Logging
- [ ] Probar envío manual desde dashboard

---

## Task 3: Notificar al Agente (ALTA PRIORIDAD)

**Archivo**: `backend/app/routers/photo_requests.py`
**Función**: `_notify_agent_of_request()` (línea ~150)

**Código actual** (PLACEHOLDER):
```python
async def _notify_agent_of_request(
    photo_request: PhotoRequest,
    assigned_user: User,
    sales_profile: SalesProfile,
    channel: str
):
    """Notify agent of new photo request."""
    # TODO: Email
    # TODO: SMS
    # TODO: WhatsApp to admin number
    # TODO: Push notification
    logger.warning(f"TODO: Implement agent notification for request {photo_request.id}")
```

**Implementación sugerida**:
```python
async def _notify_agent_of_request(
    photo_request: PhotoRequest,
    assigned_user: User,
    sales_profile: SalesProfile,
    channel: str
):
    """Notify agent of new photo request via email/SMS/WhatsApp."""
    
    # Formatear mensaje
    message_text = f"""
📸 Nueva Solicitud de Fotos

Producto: {photo_request.product_name}
Color: {photo_request.color_requested or 'No especificado'}
Tamaño: {photo_request.size_requested or 'No especificado'}
Canal: {channel.upper()}
Cliente: {photo_request.customer_id}

Dashboard: /admin/photo-requests/{photo_request.id}
"""
    
    # 1. Email (recomendado)
    if assigned_user.email:
        try:
            from app.services.email import send_email
            await send_email(
                to=assigned_user.email,
                subject=f"📸 Solicitud de fotos: {photo_request.product_name}",
                body=message_text
            )
        except Exception as e:
            logger.error(f"Error sending email: {e}")
    
    # 2. SMS (opcional, requiere Twilio)
    if hasattr(assigned_user, 'phone') and assigned_user.phone:
        try:
            from app.services.sms import send_sms
            await send_sms(
                to=assigned_user.phone,
                body=f"📸 {photo_request.product_name} ({photo_request.color_requested}) - {channel}"
            )
        except Exception as e:
            logger.warning(f"Error sending SMS: {e}")
    
    # 3. WhatsApp a admin (opcional)
    admin_phone = settings.PHOTO_REQUEST_ADMIN_PHONE
    if admin_phone:
        try:
            from app.services.whatsapp import send_whatsapp_message
            await send_whatsapp_message(
                phone=admin_phone,
                text=f"📸 {assigned_user.nombre}: {photo_request.product_name} ({photo_request.color_requested})"
            )
        except Exception as e:
            logger.warning(f"Error sending WhatsApp to admin: {e}")
    
    logger.info(f"✅ Notified agent {assigned_user.id} of photo request {photo_request.id}")
```

**Checklist**:
- [ ] Agregar User.phone field (si no existe)
- [ ] Implementar send_email() en `app/services/email.py`
- [ ] Implementar send_sms() en `app/services/sms.py` (Twilio)
- [ ] Agregar variables de entorno (emails SMTP, Twilio credentials, admin phone)
- [ ] Probar notificación cuando se crea PhotoRequest
- [ ] Agregar settings en `.env`

---

## Task 4: Wiring Frontend (ALTA PRIORIDAD)

**Archivo**: `src/components/PhotoRequestsDashboard.tsx`

**Cambios necesarios**:

```tsx
// Agregar al archivo apiClient.ts:
export async function getPhotoRequests(filters?: {
  assigned_to_me?: boolean;
  status?: string;
}) {
  const params = new URLSearchParams();
  if (filters?.assigned_to_me) params.append('assigned_to_me', 'true');
  if (filters?.status) params.append('status', filters.status);
  
  return fetch(`${API_URL}/api/photo-requests/pending?${params}`, {
    headers: { Authorization: `Bearer ${getAuthToken()}` }
  }).then(r => r.json());
}

export async function uploadPhotoMedia(
  photoRequestId: number,
  mediaUrl: string,
  mediaType: 'photo' | 'video' | '360_view'
) {
  return fetch(`${API_URL}/api/photo-requests/${photoRequestId}/media`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getAuthToken()}`
    },
    body: JSON.stringify({ media_url: mediaUrl, media_type: mediaType })
  }).then(r => r.json());
}

export async function sendPhotosToCustomer(photoRequestId: number) {
  return fetch(
    `${API_URL}/api/photo-requests/${photoRequestId}/send-to-customer`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${getAuthToken()}` }
    }
  ).then(r => r.json());
}
```

```tsx
// En PhotoRequestsDashboard.tsx, reemplazar TODOs:

const loadPendingRequests = async () => {
  setLoading(true);
  try {
    // const requests = await apiClient.getPhotoRequests({ assigned_to_me: true });  // TODO
    const requests = await getPhotoRequests({ assigned_to_me: true });
    setPendingRequests(requests);
  } catch (error) {
    toast.error('Error loading requests');
  } finally {
    setLoading(false);
  }
};

const handleUploadMedia = async () => {
  if (!selectedRequest || !mediaUrl) return;
  
  setUploading(true);
  try {
    // await apiClient.uploadPhotoMedia(selectedRequest.id, mediaUrl, 'photo');  // TODO
    await uploadPhotoMedia(selectedRequest.id, mediaUrl, 'photo');
    
    toast.success('Photo uploaded successfully');
    setMediaUrl('');
    
    // Recargar detalles
    const updated = await apiClient.getPhotoRequest(selectedRequest.id);
    setSelectedRequest(updated);
  } catch (error) {
    toast.error('Error uploading photo');
  } finally {
    setUploading(false);
  }
};

const handleSendToCustomer = async () => {
  if (!selectedRequest) return;
  
  setUploading(true);  // Reutilizar estado
  try {
    // await apiClient.sendPhotosToCustomer(selectedRequest.id);  // TODO
    await sendPhotosToCustomer(selectedRequest.id);
    
    toast.success('Photos sent to customer!');
    setSelectedRequest(null);
    
    // Recargar lista
    await loadPendingRequests();
  } catch (error) {
    toast.error('Error sending photos');
  } finally {
    setUploading(false);
  }
};
```

**Checklist**:
- [ ] Agregar 3 funciones a apiClient.ts
- [ ] Reemplazar TODO comments con llamadas reales
- [ ] Agregar importación de funciones en PhotoRequestsDashboard.tsx
- [ ] Probar carga del dashboard
- [ ] Probar upload de fotos
- [ ] Probar envío a cliente

---

## Task 5: Mejorar Diseño de BD (MEJORA)

**Archivos**: `backend/app/models/photos.py`

**Lo que falta**:
```python
# Agregar a PhotoRequest:

class PhotoRequest(Base):
    # ... campos existentes ...
    
    # NUEVO: Sales profile original
    sales_profile_id: int = Column(Integer, ForeignKey("sales_profiles.id"))
    sales_profile = relationship("SalesProfile")
    
    # NUEVO: Canal original
    channel: str = Column(String(50))  # whatsapp, messenger, instagram
    
    # NUEVO: Nombre del customer (para dashboard)
    customer_name: Optional[str] = Column(String(255))
    
    # NUEVO: Relación al usuario que asignó
    assigned_by_user_id: Optional[int] = Column(Integer, ForeignKey("users.id"))
    assigned_by_user = relationship("User", foreign_keys=[assigned_by_user_id])
```

**Migration script** (`backend/migrate_photo_requests_improvements.py`):
```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('photo_requests', 
        sa.Column('sales_profile_id', sa.Integer, sa.ForeignKey('sales_profiles.id')))
    op.add_column('photo_requests', 
        sa.Column('channel', sa.String(50)))
    op.add_column('photo_requests', 
        sa.Column('customer_name', sa.String(255)))
    op.add_column('photo_requests', 
        sa.Column('assigned_by_user_id', sa.Integer, sa.ForeignKey('users.id')))
```

**Checklist**:
- [ ] Agregar campos a modelo
- [ ] Crear migration script
- [ ] Ejecutar migración en BD existente

---

## Task 6: Tests E2E (MEDIA)

**Archivo**: `backend/test_photo_requests_e2e.py`

```python
import pytest
from app.schemas.photos import PhotoRequestCreate
from app.utils.photo_detection import detect_photo_request

def test_detect_photo_request():
    """Test photo detection patterns."""
    assert detect_photo_request("Quiero ver fotos del iPhone 15")
    assert detect_photo_request("Muéstrame imagenes en gris")
    assert detect_photo_request("Tenés foto del colores disponibles")
    assert not detect_photo_request("¿Cuál es el precio?")

@pytest.mark.asyncio
async def test_create_photo_request(client, db_session):
    """Test creating a photo request."""
    response = await client.post(
        "/api/photo-requests/create",
        json={
            "customer_id": "34600000000",
            "product_name": "iPhone 15 Pro",
            "color_requested": "gris"
        },
        params={"sales_profile_slug": "test", "channel": "whatsapp"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["color_requested"] == "gris"

@pytest.mark.asyncio
async def test_send_photos_flow(client, db_session):
    """Test complete flow: create request -> upload media -> send."""
    # 1. Crear request
    create_resp = await client.post(
        "/api/photo-requests/create",
        json={...}
    )
    request_id = create_resp.json()["id"]
    
    # 2. Cargar foto
    upload_resp = await client.post(
        f"/api/photo-requests/{request_id}/media",
        json={"media_url": "https://example.com/photo.jpg", "media_type": "photo"}
    )
    assert upload_resp.status_code == 200
    
    # 3. Enviar fotos
    send_resp = await client.post(
        f"/api/photo-requests/{request_id}/send-to-customer"
    )
    assert send_resp.status_code == 200
    data = send_resp.json()
    assert data["status"] == "completed"
    assert data["resolved_at"] is not None
```

**Checklist**:
- [ ] Escribir tests para detect_photo_request()
- [ ] Test crear PhotoRequest
- [ ] Test upload media
- [ ] Test send to customer
- [ ] Test error cases
- [ ] Ejecutar: `pytest backend/test_photo_requests_e2e.py`

---

## Prioridad de implementación

```
1️⃣ CRÍTICO (requieren antes de usar):
  - Task 1: Integración en AI Bot (para crear requests)
  - Task 2: Send to customer (para entregar fotos)

2️⃣ ALTA (necesario para operación):
  - Task 3: Notificar agente (agente se entere de solicitud)
  - Task 4: Wiring frontend (agente pueda ver dashboard)

3️⃣ MEJORA (nice-to-have):
  - Task 5: Mejorar BD (sales_profile_id, channel)
  - Task 6: Tests E2E (validar flujo)
```

---

## Comando para ejecutar todo

```bash
# 1. Backend: Agregar imports, Task 1 en ai_intelligence.py
# 2. Backend: Implementar Task 2 y Task 3 en photo_requests.py
# 3. Backend: Agregar métodos a apiClient.ts
# 4. Frontend: Wiring en PhotoRequestsDashboard.tsx
# 5. Probar:

# Terminal 1:
cd backend && python3 -m uvicorn app.main:app --reload

# Terminal 2:
npm run dev

# Prueba manual:
# 1. Ir a dashboard /photo-requests-admin
# 2. Crear request manualmente: POST /api/photo-requests/create
# 3. Dashboard muestra nuevo request
# 4. Cargar foto: POST /photo-requests/{id}/media
# 5. Enviar: POST /photo-requests/{id}/send-to-customer
# 6. Verificar en WhatsApp que cliente recibió fotos
```

---

**Status**: Documentación lista para que desarrollador implemente los 6 tasks  
**Fecha**: March 10, 2026
