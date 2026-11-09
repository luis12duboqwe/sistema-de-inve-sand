# SoftMobile — recuperación de conocimiento y migración de vendedor activa

Verificado el 9 de noviembre de 2026. Alcance exclusivo: venta de celulares. WAHA/WhatsApp público permanece desactivado.

## Información que ya existía en el VPS

- `/opt/softmobile-waha-test/knowledge/reglas.md`: formulario comercial del 6 de noviembre.
- `/opt/softmobile-waha-test/knowledge/catalogo.json`: 97 variantes, 97 precios de lista, dos variantes sin capacidad.
- `/opt/softmobile-waha-test/knowledge/softmobile-business.json`: horarios, cuatro sedes/puntos aliados, seis bancos y tasas de financiamiento, garantías, descuentos, seguimiento y **reservas no permitidas**.
- `/opt/softmobile-waha-test/media/cuentas-bancarias.jpg`: imagen bancaria recibida; no extraer ni publicar sus números.
- Informe read-only recuperado `/opt/openclaw-lab/workspace/softmobile-supervisor/KNOWLEDGE_RECOVERY.json` y `KNOWLEDGE_RECOVERY.md`.

Estos archivos no se perdieron; el Ruby anterior no los leía directamente, lo cual permitió inconsistencias entre reglas del bot y comerciales. La nueva versión incorpora cláusulas auditadas a partir del formulario y fija el SHA de los tres archivos de conocimiento: si el formulario o la lista cambian, el QA de producción falla hasta volver a revisarlos.

## Corrección y migración completada

- Ruby original activo: SHA256 `1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1`.
- Ruby comercial de noviembre promovido al archivo activo `/opt/softmobile-waha-test/sales-bot-v2.rb`: SHA256 `2c4d6d274402daa34f44f7e669efe9aaf7bc2d01574f5b53505779fb8592c885`.
- Código anterior conservado (respaldo y fuente de QA histórico) en `/opt/softmobile-waha-test/frozen-sales-baseline/sales-bot-v2-1336f52fdf4d8e44.rb`.
- Manifest de respaldo y rollback: `/opt/softmobile-waha-test/approved-sales-pilot/active-release-migration.json`. La migración revirtió automáticamente dos intentos con fallos de regresión antes de aceptar el tercero, que pasó todas las pruebas.
- Pruebas comerciales de código realmente activo: 72/72 con 12 reservas correctamente **rechazadas**; 20/20 de reglas nuevas; 18/18 reformulaciones; 11/11 casos adversariales; 6/6 rotativos; 22/22 independientes, 32/32 conversaciones profundas; 72/72 checkout ficticio; 68/68 unitarias.
- El autocorrector y Replica Skill histórico se reconectaron a la copia congelada para no perder las reglas de seguridad anteriores. Se reejecutaron y terminaron `success`. Los QA anteriores de Ruby activo se sustituyeron por `softmobile-active-sales-policy-qa.timer`, activo cada seis horas.
- Prueba del director: 38 tests; comprador activo y profundo correctamente reconocidos por SHA. Supervisor renovado. Las pruebas generales de fuente de propuesta `patch_source_compat` pasaron.
- Se mantuvieron apagados los temporizadores y servicios públicos de WhatsApp, Chatwoot/WAHA, promociones y cobros. CERO envíos a clientes, órdenes reales nuevas o cambios de inventario.

## No confundir información cargada con datos vigentes para vender

La lista de 97 precios está almacenada, pero no certificada como vigente después del 6 de noviembre. No hay confirmación en línea de unidades de proveedores por color/GB/sede, ni decisión documentada de ofrecer precios sin verificar existencias.

La base ERP tiene 458 órdenes pendientes, cero cierres contables aprobados y 173 diferencias total/ítems. No convertir en ingresos ni modificar órdenes sin comprobar su origen y documentación.

La imagen de cuentas existe, pero no prueba pagos. El banco/encargado debe verificar el ingreso, sin solicitar claves PIN/CVV.

## Información requerida del propietario

1. **Solo las actualizaciones** de precios que hayan cambiado respecto de la lista del 6 de noviembre. No reenviar el catálogo original.
2. **Fuente accesible y autorizada** de inventario real por aliado/modelo/GB/color/sede: ideal Excel/Google Sheets del encargado o flujo verificable que confirme cada solicitud. El número/foto de un responsable solo si hace falta conectar su canal en la fase final.
3. Confirmar si las 458 órdenes pendientes del ERP son operaciones históricas/test o transacciones reales. Para conciliar pagos efectivos: documentación de cobro/entrega y cierres; no es necesario compartir secretos bancarios.
4. **En la última fase**: acceso a WhatsApp Business API oficial y número(s) de prueba y aprobación específica para el lanzamiento público.

## Comprobaciones

```sh
sha256sum /opt/softmobile-waha-test/sales-bot-v2.rb
cat /opt/softmobile-waha-test/approved-sales-pilot/active-sales-policy-qa.json
cat /opt/openclaw-lab/workspace/softmobile-supervisor/KNOWLEDGE_RECOVERY.md
systemctl status softmobile-active-sales-policy-qa.timer softmobile-sales-autofix-lab.timer softmobile-replica-cycle.timer --no-pager
cat /opt/openclaw-lab/workspace/softmobile-supervisor/CERTIFICATION.json
```

La certificación 15/15 **no está conseguida**: aún depende de consentimientos persistentes, datos comerciales/contables reales, verificación de publicidad y la futura integración de transporte y autorizaciones públicas. No falsear las puertas de salida.
