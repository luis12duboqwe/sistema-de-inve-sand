# SoftMobile — autorización e integración controlada del vendedor de celulares

Fecha de autorización: **9 de noviembre de 2026**.
Alcance de la autorización aplicada: **piloto interno de ventas, sin mensajes públicos ni pagos**.

## Identidad del código

- Ruby activo antes y después: `/opt/softmobile-waha-test/sales-bot-v2.rb`, SHA-256 `1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1`.
- Candidato aprobado: SHA-256 `a4ca83e5d83244eb8552c67ad55d291eb601440b9c94c4bd614cd7d28365c06d`.
- Instalación aislada y con permisos 600: `/opt/softmobile-waha-test/approved-sales-pilot/sales-pilot-a4ca83e5d83244eb.rb`.
- Registro de aprobación: `/opt/softmobile-waha-test/approved-sales-pilot/approval.json`.
- Dictamen de prueba del archivo realmente instalado: `/opt/softmobile-waha-test/approved-sales-pilot/approved-pilot-qa.json`.

## Comprobación realizada

La integración se validó en un contenedor Ruby **sin red**, sin datos reales y sin usar la conexión de Chatwoot/WAHA.

| Prueba del archivo instalado | Resultado |
|---|---|
| Sintaxis Ruby | OK |
| 10 conversaciones de 15 turnos | 150 turnos evaluados |
| Rúbrica profunda | 32/32 |
| Casos nuevos de seguridad y lenguaje | 13/13 |
| Rúbrica independiente complementaria | 22/22 |
| Diálogos comerciales | 72/72 |
| Reformulaciones | 18/18 |
| Casos adversariales | 11/11 |
| Retos rotativos | 6/6 |
| Compra ficticia | 72/72 |
| Pruebas unitarias existentes | 68/68 |

Se instaló el servicio `softmobile-approved-sales-pilot-qa.service` y temporizador `softmobile-approved-sales-pilot-qa.timer`. Realiza la misma verificación de integridad y regresión del **archivo aprobado**, cada seis horas. Prueba manual bajo systemd: resultado `success`.

## Medidas de aislamiento

- **No se reemplazó** el Ruby activo: los procesos de autocorrección todavía fijan el SHA antiguo, por lo que reemplazarlo sin migrar sus dependencias rompería la automatización.
- Los temporizadores `softmobile-waha-catalog-notes.timer`, `softmobile-ai-agent-public-pilot.timer` y `softmobile-combined-pilot-promotion.timer` siguen deshabilitados e inactivos.
- No se actualizó la configuración del remitente, el transporte, las claves ni las bases de datos.
- El paquete aprobado no habilita compras, apartados reales, reembolsos, financiamiento ni extracción de clientes.
- Las referencias de precio, stock y cuotas de aliados continúan pendientes de verificación.
- La certificación general de lanzamiento sigue bloqueada. Ninguna aprobación de pruebas ficticias sustituye su autorización final.

## Comprobar y revertir

```sh
python3 /opt/openclaw-lab/supervisor/approve_sales_pilot.py --check
systemctl status softmobile-approved-sales-pilot-qa.service softmobile-approved-sales-pilot-qa.timer --no-pager
cat /opt/softmobile-waha-test/approved-sales-pilot/approved-pilot-qa.json
sha256sum /opt/softmobile-waha-test/sales-bot-v2.rb /opt/softmobile-waha-test/approved-sales-pilot/*.rb
```

Para suspender el monitoreo de este paquete sin afectar otras funciones:

```sh
systemctl disable --now softmobile-approved-sales-pilot-qa.timer
```

En caso de rechazar la versión, detener su temporizador y retirar **únicamente** el directorio `approved-sales-pilot` tras conservar el manifiesto de auditoría. No hay que restaurar el Ruby activo porque jamás se sustituyó.

## Siguiente compuerta

Migrar cuidadosamente las pruebas y scripts que están fijados al SHA anterior; luego validar datos de stock/precios, consentimiento y órdenes reales. Solo después plantear un despliegue restringido y reversible del vendedor. WhatsApp y la salida pública siguen fuera del alcance autorizado en esta etapa.
