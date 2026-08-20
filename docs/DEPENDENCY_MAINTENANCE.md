# Mantenimiento de dependencias

Durante el cierre y la operación estable del sistema, las actualizaciones automáticas de dependencias deben reducir ruido y evitar introducir cambios incompatibles sin una revisión dedicada.

## Política

- Dependabot para npm se ejecuta semanalmente.
- Las actualizaciones `minor` y `patch` se agrupan en un único PR compatible cuando sea posible.
- Las actualizaciones `major` no se proponen automáticamente y deben revisarse como trabajo de mantenimiento separado.
- Los escaneos de seguridad del CI (`npm audit`, `pip-audit` y Trivy) permanecen como controles independientes del calendario de Dependabot.
- Una actualización mayor sólo debe entrar con pruebas completas y fuera de una ventana de despliegue/corte de datos.

## Motivo

El objetivo es mantener una base estable durante producción sin dejar de detectar vulnerabilidades mediante los security gates existentes. Los saltos mayores pueden cambiar APIs, configuración o comportamiento y no deben mezclarse con un release operativo.
