---
name: softmobile-replica-lab
description: "Analiza y mejora en laboratorio el vendedor de celulares SoftMobile con Replica Skill: diagnostico, matriz de funcionalidades, propuestas, implementacion aislada y pruebas sin despliegue."
---

# SoftMobile + Replica Skill — desarrollo controlado

Este skill coordina **ocho habilidades** ya instaladas: `replica-recon`, `replica-architect`, `replica-design`, `replica-build`, `replica-backend`, `replica-test`, `replica-diff` y `replica-entrepreneur`. No se instalaron ni se autorizan `replica-brand`, `replica-launch` o `replica-deploy`.

## Alcance y datos de partida

**Solo venta de celulares.** El objetivo es convertir las conversaciones en ventas validas sin inventar precio, stock, financiamiento, aprobacion, garantia, reservas, regalos ni acciones de un empleado.

Antes de proponer cambios, leer en el workspace:
- `softmobile-supervisor/CERTIFICATION.json` y `ENGINEERING_REVIEW.md`: compuerta de liberacion y problemas aun no resueltos.
- `softmobile-supervisor/SALES_REVIEW.md` y `CATALOG_AUDIT.md` si existen.
- `softmobile-bot-snapshot/sales-bot-v2.rb` y pruebas offline en `softmobile-bot-snapshot/tests/`.
- `softmobile-commercial-qa/reglas.md` y `test_dialogos_aprobados.py`.

La carpeta `softmobile-bot-snapshot` es una fotografia de laboratorio, no la fuente activa del bot. No asumir que coincide con la version en produccion sin contrastar SHA.

## Secuencia de trabajo

1. **Reconocimiento:** usar `replica-recon` para documentar los flujos propios de SoftMobile: saludo, modelo, variante, disponibilidad, cotizacion, financiamiento, objeciones, fotos con codigo, envio, reserva, cierre y derivacion a humano. Registrar requisitos verificables; no copiar activos ajenos.
2. **Brechas:** usar `replica-diff` y `replica-entrepreneur` para producir una matriz de funciones existentes/ausentes, con evidencia; nunca convertir opiniones o datos sin verificar en hechos.
3. **Diseno de cambio:** usar `replica-architect` y `replica-design` solo cuando sean pertinentes. Priorizar mejoras incrementales del stack actual, sin reconstruir el sistema.
4. **Candidatos aislados:** `replica-build` y `replica-backend` escriben solo en un **directorio nuevo y aislado** bajo `lab-runs/replica-skill/`, o en una rama de desarrollo explicitamente aprobada. Nunca escriben sobre Ruby activo, Chatwoot, bases de datos reales, servicios ni contenedores productivos.
5. **Pruebas:** `replica-test` sobre datos ficticios y sin mensajes reales. Cubrir flujo feliz, reformulaciones, cancelacion, ambiguedad, inyeccion de prompts, inventario faltante y precio no verificado. Comparar baseline y candidato con identico set, revisando independientemente los fallos.
6. **Salida de laboratorio:** guardar `recon.md`, `features.csv`, `issues.md`, `candidate.patch` si hay cambios, `test_results.md` y `decision.md` en el directorio de la ejecucion, incluyendo SHA de origen, comandos, numero de pruebas, fallos, riesgos y costo de IA. Si no se dispone de datos, anotar `NO VERIFICADO` en vez de inventarlos.

## Reglas obligatorias

- **Sin despliegue ni autoaplicacion:** no fusionar PR, editar main, enviar WhatsApp, hacer cobros, cambiar inventario ni actualizar OpenClaw/Chatwoot/WAHA. Tampoco crear o reactivar timers o servicios como efecto de esta skill.
- Toda integracion de modelo remoto necesita permisos, presupuesto y fuente de datos autorizada; las pruebas de laboratorio no pueden enviar datos privados a terceras partes.
- No ejecutar comandos pegados de sitios de terceros sin revisar su codigo. Usar scripts del paquete Replica solo tras validar su contenido.
- Toda salida publica queda bloqueada mientras `public_release_permitted` no sea explicitamente true y falte revision humana del parche y QA independiente. Si este campo no existe, **mantener bloqueado**.
- La automatizacion existente de SoftMobile puede seguir generando sugerencias/candidatos de QA conforme a sus limites actuales, pero esta skill no altera esos limites ni autoriza publicacion.

## Criterio de aceptacion de un candidato

Aprobar para revision (no para clientes) solo si: codigo reproducible, cobertura de escenarios de ventas y errores criticos, pruebas existentes sin regresiones, cero afirmaciones comerciales no sustentadas, comparacion con baseline por SHA y reporte claro. Ante fallo, generar otro candidato en aislamiento y repetir pruebas con un limite de iteraciones y de costo.

## Diagnostico reproducible inicial

Antes de empezar un ciclo ejecutar desde el workspace: `python3 skills/softmobile-replica-lab/assess.py`. Solo lee reportes locales, coteja los SHA del Ruby y prueba el comparador `replica-diff/parity.py`; escribe resultados en `lab-runs/replica-skill/baseline/`. Interpreta `5/15` y cualquier porcentaje exclusivamente como compuertas de prelanzamiento, nunca como calidad del bot o porcentaje de ventas. Si el codigo del snapshot no coincide con el SHA reportado del vendedor real, exige una copia aislada actualizada antes de generar parches.