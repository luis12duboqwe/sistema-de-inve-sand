# Replica Skill + OpenClaw — laboratorio de ventas SoftMobile

## Estado instalado

- Paquete Replica Skill de `Jakeschincariol/replica-skill`, commit upstream `77c9436fb3d18c3d58169efb8caf4fe906b0dc51`, 57/57 pruebas originales pasadas.
- Ocho skills en `/opt/openclaw-lab/workspace/skills/replica-*`; **no** se habilitan `replica-deploy`, `replica-launch`, `replica-brand`.
- Skill coordinadora `softmobile-replica-lab` en `/opt/openclaw-lab/workspace/skills`.
- El autofix de ventas existente genera **candidatos limitados a recetas revisadas** y los prueba cada seis horas mediante `softmobile-sales-autofix-lab.timer` (`00,06,12,18:46 UTC`).
- `softmobile-replica-cycle.timer` ejecuta una segunda pasada cada seis horas (`01,07,13,19:14 UTC`). Valida SHA de fuente activa y parche, bloqueos de seguridad, realiza pruebas en Docker **sin red**, compara las seis familias comerciales con el comparador `replica-diff`, y entrega reporte para revision. No aplica parches automaticamente.

## Flujo operativo

1. Leer Ruby activo congelado `/opt/softmobile-waha-test/sales-bot-v2.rb` sin modificarlo.
2. El generador previo calcula propuestas seguras y hasta 4 intentos; guarda el candidato Ruby y parche en `laboratorio-ia/quality/autonomous-sales/candidates/`.
3. `replica_cycle.py` valida sellos SHA-256, tiempos, diff completo, flags, ruta y compuerta de lanzamiento.
4. `replica_qa_probe.py` repite QA sobre el mismo candidato: 72 conversaciones, 18 holdout, 11 escenarios adversariales, 6 rotativos, 72 checkout ficticios y al menos 68 pruebas unitarias.
5. Se generan `recon.md`, `features.csv`, `parity.md`, `issues.md`, `test_results.json`, `decision.md` y resúmenes `latest.json` y `latest.md` dentro de `/opt/openclaw-lab/workspace/lab-runs/replica-skill/`. Nunca se guarda contenido de clientes reales.
6. Si una comprobación falla: `status=blocked`, ejecución rechazada y registro de motivo; sin despliegue, sin mensajes públicos, sin cambios de inventario. Si todo pasa: `qa_passed_review_required`; **todavía no** significa lanzamiento ni revisión independiente completada.

## Evidencia actual

- Código fuente fijado al SHA `1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1`.
- Candidato probado SHA `6fe7a1cd7278dd31303d414e95d5089a4797bf591e0ab58a3b56af6bdeefec94`.
- La segunda pasada completa y el servicio systemd finalizaron con éxito. Pruebas de seguridad por inyección de fallos: **9/9**.
- El autocorrector y el revisor usan rúbricas del mismo laboratorio. La repetición **no** constituye certificación independiente de una segunda rúbrica.
- Certificación pública continúa bloqueada. Los datos de precios/stock de aliados, órdenes reales, decisiones de negocio y WhatsApp no se consideran verificados.

## Inspección y recuperación

```sh
systemctl list-timers --all | grep -E 'softmobile-(sales-autofix-lab|replica-cycle)'
systemctl status softmobile-replica-cycle.service softmobile-replica-cycle.timer --no-pager
journalctl -u softmobile-replica-cycle.service --no-pager -n 50
cat /opt/openclaw-lab/workspace/lab-runs/replica-skill/latest.md
cd /opt/openclaw-lab/supervisor && python3 -m unittest -v test_replica_cycle
```

Desactivar solo el ciclo Replica (sin afectar autocorrector existente):
`systemctl disable --now softmobile-replica-cycle.timer`.

## Limitaciones de autonomía

El generador **no** escribe software libremente ni llama a un modelo de pago: elige y modifica solo recetas previamente revisadas, con máximo cuatro intentos. Replica Skill añade estructura de reconocimiento, matriz de alcance, pruebas y comparación automatizados. No se activa agente LLM para programación arbitraria, auto-fusión, despliegue, financiación, atención por WhatsApp, uso de credenciales, ni tareas con red. Para superar estas limitaciones hace falta QA independiente, revisión de diff y validación de fuentes reales; no se debe interpretar la instalación como una garantía de calidad de nivel producción.