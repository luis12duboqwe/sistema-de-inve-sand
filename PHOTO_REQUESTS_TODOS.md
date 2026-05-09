# Estado Actual: Sistema de Solicitudes de Fotos

## Resumen

El flujo principal de solicitudes de fotos ya está implementado en backend y frontend.

## Completado

- Modelos de BD: `PhotoRequest`, `PhotoRequestMediaItem`.
- Schemas Pydantic: create, update, response, summary y detalle.
- Router API en `backend/app/routers/photo_requests.py`.
- Detección desde IA en `backend/app/routers/ai_intelligence.py` usando `detect_photo_request()`.
- Creación interna con `create_photo_request_internal()` y asignación automática de agente.
- Dashboard de agente en `src/components/PhotoRequestsDashboard.tsx`.
- Métodos de API client para listar, reclamar, cargar media, subir archivos, enviar al cliente y actualizar estado.
- Envío al cliente por WhatsApp/Messenger/Instagram/Facebook cuando las credenciales del canal están configuradas.
- Upload local/S3 mediante `get_storage_manager()`.
- Notificación por email al agente si SMTP está configurado.
- WebSocket para eventos de claim/upload.

## Pendiente Real

- Configurar credenciales reales por canal (`WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `META_PAGE_ACCESS_TOKEN` o `channel_integrations` por perfil).
- Configurar SMTP si se requiere notificación por email fuera del dashboard.
- Validar el flujo completo con un mensaje real de N8N/WhatsApp en ambiente staging.
- Mejorar UX para carga múltiple de fotos en una sola acción.
- Agregar métricas de tiempo de respuesta del agente y satisfacción del cliente.

## Pruebas Recomendadas

1. Enviar un mensaje tipo `Quiero ver fotos del iPhone 15 en gris` al endpoint de IA.
2. Confirmar que se crea un `PhotoRequest` con `sales_profile_id`, `origin_channel` y `assigned_to_user_id`.
3. Abrir el dashboard de fotos, reclamar la solicitud y subir una imagen.
4. Ejecutar `send-to-customer` con credenciales reales del canal.
5. Confirmar que los media items quedan con `sent_to_customer_at` y la solicitud pasa a `completed`.

**Última actualización**: May 4, 2026