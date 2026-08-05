# Go/No-Go Checklist de Producción

## Infraestructura

- [ ] Dominio y DNS apuntando al servidor final.
- [ ] HTTPS/TLS activo y certificado válido.
- [ ] Firewall: solo puertos necesarios abiertos.
- [ ] PostgreSQL con almacenamiento persistente y monitoreado.

## Configuración

- [ ] Archivo deploy/.env.prod creado y protegido con permisos 600.
- [ ] Variables críticas sin placeholders (SECRET_KEY, CHANNEL_ENCRYPTION_KEY, DB, Grafana).
- [ ] ENVIRONMENT=production y DEBUG=false.
- [ ] ALLOWED_HOSTS y CORS_ORIGINS restringidos.

## Calidad y Pruebas

- [ ] npm run lint sin errores.
- [ ] npm run build exitoso.
- [ ] pytest tests/e2e en verde.
- [ ] Flujos críticos validados manualmente (orden, transferencia, IMEI, devolución, cierre).

## Seguridad

- [ ] npm audit (high+) en estado aceptable.
- [ ] pip-audit sin hallazgos críticos sin mitigar.
- [ ] Trivy fs/image sin vulnerabilidades críticas abiertas.
- [ ] Rate limiting y lockout de login verificados.

## Observabilidad

- [ ] /api/health responde OK.
- [ ] /api/ready responde ready.
- [ ] /api/metrics y /api/metrics/prometheus exponen métricas.
- [ ] Prometheus scrapea backend.
- [ ] Alertmanager entrega alerta al webhook configurado.
- [ ] Dashboard en Grafana con métricas clave.

## Backups y DR

- [ ] Backup manual ejecutado y checksum generado.
- [ ] Restauración validada con restore-backup.sh.
- [ ] Simulacro DR ejecutado con dr-drill.sh.
- [ ] RTO/RPO medidos y dentro de objetivo del negocio.

## Go-Live

- [ ] Ejecutado deploy/prod-gate.sh sin fallos.
- [ ] Ventana de despliegue aprobada.
- [ ] Plan de rollback documentado y probado.
- [ ] Owner de guardia definido para primeras 24h.
