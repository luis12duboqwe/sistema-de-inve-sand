# Configuración segura de WhatsApp, Messenger e Instagram — SoftMobile

Esta guía sustituye las instrucciones antiguas que confundían el token de desafío de Meta con la autenticación de mensajes y recomendaban borrar credenciales reales.

## Prerrequisitos operativos

- Desplegar exclusivamente una versión cuyo CI y gate de producción estén aprobados, con TLS y credenciales gestionadas fuera de Git.
- Asociar cada cuenta de canal con su `SalesProfile` y su identificador real: `phone_number_id` para WhatsApp, `page_id` para Messenger, `instagram_account_id` para Instagram.
- Configurar `META_APP_SECRET` del aplicativo de Meta y tokens de acceso del canal. En producción, sin secreto de firma no se deben aceptar mensajes POST.
- Validar permisos de cuenta, página, bandeja, sucursal y destinatario antes de cualquier respuesta automática.
- Mantener un plan de gestión de duplicados, reintentos e incertidumbre de entrega.

## Dos mecanismos distintos de verificación

**GET de alta del webhook:** Meta solicita `hub.mode`, `hub.verify_token` y `hub.challenge` al endpoint `/api/channels/<canal>/webhook`. El *verify token* sirve para validar el desafío de suscripción, **no autentica el mensaje posterior**.

**POST de eventos:** verificar el encabezado `X-Hub-Signature-256`, HMAC-SHA256 sobre los bytes originales del cuerpo y la clave del aplicativo de Meta. Una firma ausente, errónea o con secreto de firma no configurado debe ser rechazada antes de cualquier escritura. Nunca calcular la firma con el *verify token* ni con la contraseña del usuario.

Los endpoints son:
- `GET /api/channels/whatsapp/webhook`, `POST /api/channels/whatsapp/webhook`
- `GET /api/channels/messenger/webhook`, `POST /api/channels/messenger/webhook`
- `GET /api/channels/instagram/webhook`, `POST /api/channels/instagram/webhook`

## Validación y respuesta

1. Configurar las credenciales **reales** sólo en el entorno/secret manager autorizado. No copiar secretos a archivos Markdown.
2. Registrar URL HTTPS y verify token ante Meta, y comprobar el desafío GET.
3. En un entorno de pruebas separado, enviar un POST con firma HMAC válida: debe registrarse como evento autorizado. Una firma vacía, alterada o secreta ausente debe rechazar y dejar las tablas sin cambios.
4. Probar deduplicación de `message_id`, aislamiento entre cuentas/canales, idempotencia y comportamiento ante pérdida de respuesta antes de responder a clientes.
5. Comprobar por separado el identificador de entrega del proveedor. Un HTTP 200 del webhook entrante **no demuestra que se entregó una respuesta saliente**.
6. Usar `GET /api/channels/health` y pruebas de conexión con permisos administrativos como pistas de configuración, no como certificación de delivery.

## Pruebas y protección de credenciales

- Las pruebas negativas se encuentran en `backend/tests/test_channel_webhook_delivery_integrity.py` y las pruebas HMAC añadidas en el PR de auditoría.
- No ejecutar `seed_channel_credentials.py --clear`, `--generate` ni `--populate` sobre un entorno que contenga credenciales reales: podrían reemplazar o eliminar configuración. Para laboratorio se requiere una base descartable.
- Ante error de firma, revisar primero el App Secret usado, la autenticidad del cuerpo y el header de Meta; nunca borrar tokens para “reparar” una firma inválida.
- Para n8n, consultar `docs/INTEGRACION_N8N.md`. Su flujo de ejemplo responde a un webhook de prueba; no envía por sí solo un mensaje saliente Meta.

**Prohibido habilitar tráfico productivo hasta validar firma, cuenta de origen, idempotencia y entrega real con credenciales de prueba.**
