# SoftMobile — reparación del ciclo autónomo comercial (9 nov 2026)

## Diagnóstico causal

La suite `commercial` previa ejecutaba 47 pruebas y fallaba exactamente en cinco casos (`test_dialogos_aprobados.Conversaciones`):
- `test_ai_untrusted_price` exigía L 16,700 desde `ReferenceCatalog`, que explícitamente **no valida precios**, colores ni existencias.
- `test_ai_multi_turn_payment` y `test_provider_outage_keeps_commercial_context` exigían L 17,368 sin precio verificado de la unidad.
- `test_unknown_outage_handoff` y `test_pilot_unknown_outage_handoff` exigían asegurar que un encargado respondería sin confirmar asignación real.

El mecanismo de IA devolvía respuestas conservadoras correctas, pero las pruebas antiguas las marcaban incorrectas. El ciclo estaba fijado a `MAX_PASSES=1`, y los fallos hacían imposible obtener dos revisiones limpias.

## Corrección técnica

El archivo histórico `test_dialogos_aprobados.py` **permanece intacto** (SHA256 fijado a `a6e90d05d9452c559eefeb534beb4b3bdf13e828563e4df331362432f650d20f`). Se instala un contrato de prueba versionado `policy_contracts/test_commercial_policy_contract.py` sobre cada **copia aislada**, que hereda los 31 casos no conflictivos y reemplaza únicamente esos cinco criterios por otros que prohíben cotizaciones no verificadas y afirmaciones de traspaso inexistente. Los otros módulos comerciales de pruebas (6+5 casos) siguen intactos. La suite comercial vuelve a **47/47**, sin fingir precio/stock ni alterar el vendedor.

`lab_cycle.prepare` aplica el contrato con verificación SHA; cualquier cambio del test original exige una nueva revisión de ingeniería y no se sustituye silenciosamente.

`review_loop.py` admite **máximo 3 turnos por ciclo**, pero también limita **6 turnos por día UTC** mediante registro persistente previo a la llamada remota. Ledger corrupto bloquea llamadas. Si los tests fallan y un turno no modifica código, se detiene anticipadamente para no agotar presupuesto sin avances. Permite dos revisiones independientes consecutivas, incluso cuando la reparación se haya completado en la misma ejecución. Cada sesión del revisor tiene identificador independiente y la huella del alcance incluye el nuevo contrato de seguridad.

Se mantienen el tiempo de espera entre ejecuciones, el bloqueo de cambios a producción, revisión de parches y pruebas en Docker sin red. El límite diario no considera otros agentes o facturación global de la API, solo este ciclo.

## Alcance y límites

- El contrato actualizado es para **referencias NO verificadas**. Los tests restantes de respuestas históricas aún aceptan cifras de un catálogo de pruebas; esto **NO autoriza** esas cifras en atención pública. El inventario y precios de aliados requieren una fuente comercial autorizada.
- No se modificaron `/opt/softmobile-waha-test/laboratorio-ia/*.py`, `sales-bot-v2.rb`, ventas reales ni servicios de WhatsApp/Chatwoot.
- Ni el contrato ni el nuevo ciclo equivalen a certificación independiente externa, autorización de precios, conciliación de pedidos o permiso de lanzamiento.
- El supervisor y su matriz de liberación siguen siendo la autoridad para publicación. Todos los parches del laboratorio son candidatos sin despliegue.

## Comprobar

```sh
cd /opt/openclaw-lab/integration
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -q test_review_retry_budget test_review_convergence test_safe_promote
cat /opt/openclaw-lab/results/lab-cycles/latest.json
cat /opt/openclaw-lab/results/lab-cycles/agent-calls-by-utc-day.json
systemctl status softmobile-openclaw-lab.timer softmobile-openclaw-lab.service --no-pager
```

Desactivar solo el temporizador de auditoría de OpenClaw sin detener otras aplicaciones: `systemctl disable --now softmobile-openclaw-lab.timer`. No habilitar servicios públicos para comprobar el laboratorio.