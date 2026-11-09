# SoftMobile — Auditoría real de los 15 controles de lanzamiento

Última evaluación: 9 de noviembre de 2026, UTC.
Alcance: **ventas de celulares**. Reparaciones fuera de alcance. WhatsApp al final.

## Resultado oficial verificado

**7 de 15 controles**. Preparación técnica/comercial sin WhatsApp: **9 de 12**.
Candidato de vendedor Ruby aprobado para piloto interno en aislamiento, sin mensajes públicos ni modificaciones al Ruby activo.

### Controles que aprobaron

1. Coherencia entre snapshots.
2. Ejecución segura de operaciones internas.
3. Cobertura básica del piloto Chatwoot.
4. Pruebas locales de código.
5. Simulaciones comerciales ficticias.
6. Convergencia de las revisiones independientes del código del laboratorio.
7. Compatibilidad del origen Ruby y del guard de propuestas, comprobada de forma dinámica con SHA y posición de anclaje; **NO implica permiso de despliegue**.

La fuente del vendedor Ruby activo permanece con SHA `1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1`.
El candidato aprobado para piloto interno tiene SHA `a4ca83e5d83244eb8552c67ad55d291eb601440b9c94c4bd614cd7d28365c06d`.
El nuevo certificador verifica ambos y conserva explícitamente la distinción entre la calidad del candidato y el vendedor activo. El segundo pasa 72/72 en la rúbrica comercial y 32/32 en conversaciones profundas; **el vendedor activo sigue en 36/72**.

### Ocho controles todavía bloqueados

| Control oficial | Evidencia real que hace falta |
|---|---|
| `real_ruby_reply_quality_passed` | Promover en privado con backup y rollback el Ruby revisado, migrar las dependencias de SHA del autocorrector y obtener 72/72 **sobre el archivo realmente activo** |
| `pilot_transport_verified` | Confirmar transporte WhatsApp activo en el piloto, sin habilitar conversaciones generales antes de la fase final |
| `real_whatsapp_chatwoot_full_cycle_verified` | Verificar entrega y recepción, deduplicación, handoff a humano y consentimiento mediante números de prueba |
| `followup_consent_policy_verified` | Guardar y aplicar opt-out/no-contacto a todos los seguimientos, incluso después de reinicios y reintentos |
| `commercial_actions_authorized` | Aprobar fuente fiable de existencias/precios de aliados, condiciones de entrega, financiación, cobros y devoluciones |
| `explicit_owner_launch_approval` | Aprobación **específica para lanzar públicamente**, distinta de la autorización de piloto interno, una vez listas las condiciones |
| `real_orders_reconciled` | Conciliación con comprobantes reales y cierres autorizados; no convertir pendientes en ingresos artificiales |
| `meta_ads_data_connected` | Fuente Meta Ads operativa, autenticada, refrescable dentro del sistema, con seguimiento de campañas y atribución |

## Datos no conciliados, del informe agregado del ERP

- 458 órdenes pendientes, 0 órdenes completadas y 0 cierres diarios aprobados.
- 173 diferencias entre total de orden y suma de ítems; 153 pueden involucrar comisiones de tarjetas o financiación, pero **todavía no se han validado con comprobantes**.
- 135 artículos activos sin stock, 3 precios registrados debajo del costo y una unidad con especificación incompleta.
- Stock y precios de aliados no conectados con verificación de frescura.

No modificar automáticamente importes, estados de orden, cobros ni cantidades de inventario para pasar el control.

## Publicidad Meta

Se pudo recuperar por Metricool la cuenta de Meta Ads conectada a SoftMobile y consultar las métricas de impresiones, gasto y clics del período 2–8 de noviembre de 2026 (todos los valores recibidos fueron cero). Esto **no prueba rentabilidad** ni constituye una integración persistente de métricas dentro del VPS.

Supermetrics tiene la prueba vencida y Windsor.ai informa que excede el límite de cuentas del plan gratuito, por lo que esas otras rutas no entregaron métricas. Falta una fuente operativa de anuncios y atribución de ventas.

## Mejoras que quedaron implementadas

- `release_gate.py`: comprueba el SHA del Ruby realmente activo y la compatibilidad del generador de propuestas; no se limita a un valor `False` fijo para el guard técnico.
- El mismo certificador verifica el candidato **aprobado para piloto interno** contra el SHA del archivo de QA instalado, sin declarar que el candidato sea el vendedor público.
- 50 pruebas unitarias de seguridad, incluyendo seis nuevas contra suplantar certificación con hashes incorrectos, cambios no autorizados o informes del candidato como si fueran informes de producción.
- `certification_blockers.py`: crea dos informes sanitizados, `CERTIFICATION_BLOCKERS.json` y `CERTIFICATION_BLOCKERS.md`. Se ejecuta al finalizar el certificador.
- Los 15 controles originales se conservaron, con salida pública bloqueada. No se falsificaron pruebas ni permisos.

## Fuentes y comandos de inspección

```sh
cat /opt/openclaw-lab/workspace/softmobile-supervisor/CERTIFICATION.json
cat /opt/openclaw-lab/workspace/softmobile-supervisor/CERTIFICATION_BLOCKERS.md
cat /opt/softmobile-waha-test/approved-sales-pilot/approved-pilot-qa.json
cd /opt/openclaw-lab/supervisor && python3 -m unittest -q test_release_gate
systemctl status softmobile-release-gate.service softmobile-certification-blockers.service --no-pager
```

No se autorizó el lanzamiento público ni se activaron WhatsApp, pagos, publicidad ni envíos de mensajes. La meta 15/15 exige evidencia técnica y comercial real; no es válido cambiar su denominador o marcar en verde controles pendientes.