# Estado de Funcionalidades de IA

## Resumen

El sistema contempla varias funcionalidades avanzadas con Inteligencia Artificial. Este documento detalla el **estado actual de implementación** de cada una, lo que está **completo**, lo que está **en fase beta** y lo que requiere **implementación adicional**.

### Decisión v2.0 (3 Ene 2026)
- El módulo IA se libera como **BETA supervisada**: heurísticas locales siempre disponibles y OpenAI opcional.
- El flag `ENABLE_AI_FEATURES` gobierna toda la ruta `/api/ai/*`; si está en `false`, la API devuelve `HTTP 503` para evitar exponer funcionalidades parcialmente configuradas.
- Solo habilitar el flag en entornos donde existan N8N + OpenAI configurados y documentados.

---

## 1. Bots Conversacionales de Ventas (GPT-4)

### Estado: ✅ **IMPLEMENTADO (Backend) - ⚠️ INTEGRACIÓN PENDIENTE**

### Descripción
Bots de IA que interactúan con clientes a través de WhatsApp, Facebook e Instagram para:
- Responder preguntas sobre productos
- Mostrar disponibilidad de inventario
- Asistir en negociaciones con límites de descuento configurables
- Gestionar financiamiento y trade-ins
- Escalar a humanos cuando sea necesario

### Componentes Implementados

#### Backend (`backend/app/routers/ai_intelligence.py`):
- ✅ `POST /api/ai/context` - Genera contexto para chat de IA
  - Perfil del bot (tono, personalidad, límites)
  - Inventario relevante de todas las ubicaciones
  - FAQs relacionadas
  - Información de financiamiento
  - Historial de cliente
  - Contexto de conversación previa

- ✅ `POST /api/ai/log-interaction` - Registra interacciones
  - Tracking de tokens usados
  - Historial de conversaciones
  - Métricas de uso

- ✅ `POST /api/ai/submit-for-training` - Cola de entrenamiento
  - Preguntas frecuentes no resueltas
  - Sugerencias de mejora

- ✅ `GET/POST /api/ai/config/{sales_profile_id}` - Configuración
  - Modelo de IA (gpt-4, gpt-4o)
  - Temperatura (creatividad)
  - Tono de voz
  - Límites de descuento
  - Condiciones de escalamiento

- ✅ `GET /api/ai/status` - **NUEVO** snapshot consolidado
  - Métricas de actividad de cada bot (interacciones, tokens, backlog)
  - Conteo de clientes bloqueados/trolls
  - Alertas de pronóstico (productos por agotarse)
  - Requiere permiso `reports:view`

#### Frontend:
- ✅ Componentes de configuración (posiblemente en diálogos de SalesProfile)
- ⚠️ **PENDIENTE**: Interfaz de chat en tiempo real
- ⚠️ **PENDIENTE**: Dashboard de métricas de bot

### Integración Requerida

#### N8N Workflow (CRÍTICO):
El flujo completo requiere un workflow de N8N que:

1. Recibe mensaje de WhatsApp/Facebook/Instagram
2. Llama a `POST /api/ai/context` para obtener contexto
3. Envía contexto + mensaje a OpenAI API
4. Recibe respuesta de GPT-4
5. Registra interacción con `POST /api/ai/log-interaction`
6. Envía respuesta al cliente
7. Detecta gatillos de escalamiento (notificar admin)

**Archivos relevantes**: `docs/INTEGRACION_N8N.md`, `simulate_whatsapp_flow.py`

#### Configuración Pendiente:
```bash
# En .env o .env.production
OPENAI_API_KEY=sk-tu-clave-real-de-openai
OPENAI_MODEL=gpt-4o
N8N_WEBHOOK_URL=https://n8n.tu-dominio.com/webhook/whatsapp
N8N_AUTH_TOKEN=tu-token-secreto
ENABLE_AI_FEATURES=true
```

> **Importante:** Si `ENABLE_AI_FEATURES=false`, cualquier endpoint bajo `/api/ai/*` responderá `503 Service Unavailable` mediante la dependencia `_ensure_ai_features_enabled`. Esto aplica incluso a rutas que ofrecen heurísticas locales (`business-insights`, `context`, etc.).

### Testing
```bash
# Simular flujo de WhatsApp
python simulate_whatsapp_flow.py
```

### Métricas Operativas Centralizadas

- El endpoint `GET /api/ai/status` devuelve un payload listo para dashboards:
  - `ai_profiles`: lista ordenada por actividad con últimos 7 días de interacciones y tokens.
  - `interactions_last_24h`, `tokens_last_24h`, `avg_tokens_per_response`: salud global del sistema.
  - `training_backlog`: items pendientes en `TrainingQueue` por perfil.
  - `forecasting_alerts`: hasta 5 productos con restock recomendado o <10 días de stock.
- Ideal para alimentar un panel en Next.js/React o para alertar vía Slack/N8N.

---

## 2. Pronósticos de Ventas (Forecasting)

### Estado: ✅ **IMPLEMENTADO (Backend Básico)**

### Descripción
Predicción de ventas a 30 días basada en histórico para:
- Planificación de inventario
- Detección de tendencias
- Alertas de bajo stock anticipadas

### Componentes Implementados

#### Frontend (`src/hooks/use-forecasting.ts`):
- ✅ Regresión lineal simple en cliente
- ✅ Cálculo de tendencias básicas
- ⚠️ **LIMITACIÓN**: Solo usa datos en memoria (no histórico completo de BD)

#### Backend (`backend/app/routers/forecasting.py`):
- ✅ Endpoint dedicado: `GET /api/forecasting/predict`
- ✅ Cálculo optimizado sobre todo el histórico de la BD
- ✅ Algoritmo de tendencia y crecimiento conservador
- ✅ Servicio reutilizable `app/services/forecasting_service.py` (usado por `/api/ai/status`)
- ❌ **PENDIENTE**: Algoritmos avanzados (ML) o Jobs asíncronos

### Implementación Recomendada

Para producción ya se cuenta con:

1. **Endpoint avanzado**: `POST /api/analytics/forecast` soporta filtros (`product_ids`, `location_id`, `min_confidence`, `trend`) y puede reutilizar el snapshot cacheado si `use_cache=true`. El servicio base (`generate_sales_forecasts`) también alimenta `GET /api/forecasting/predict` y `GET /api/ai/status`.
2. **Job programado**: `app/jobs/forecasting_job.py` usa APScheduler para recalcular diariamente (03:00 UTC) siempre que `ENABLE_FORECAST_SCHEDULER=true`. Los resultados viven en `app.state.forecast_cache` y se sirven sin golpear la BD.
3. **Camino a ML** (Fase 2): Mantener backlog para integrar modelos Prophet/ARIMA, estacionalidad avanzada y señales externas (promociones, calendario). El pipeline actual deja un solo punto de extensión (`summarize_forecasts`).

### Alternativa Actual (MVP)
Para versión inicial, usar el forecasting del frontend:
- ⚠️ Marcar como "BETA" en UI
- ⚠️ Documentar que es predicción simple (no ML avanzado)
- ⚠️ Limitar a productos con >30 días de histórico

---

## 3. Insights de Negocio (GPT-4)

### Estado: ✅ **Backend con métricas y caché** · ⚠️ **GPT-4 opcional**

### Descripción
Análisis con IA de métricas de negocio para sugerir:
- Productos a restockear
- Oportunidades de precio
- Productos de bajo movimiento
- Optimizaciones de inventario

### Componentes Implementados

#### Frontend (`src/hooks/use-optimization-insights.ts`):
- ✅ Cálculos de insights locales (sin IA real)
- ✅ Detección de bajo stock
- ✅ Identificación de productos lentos
- ✅ UI para mostrar insights

#### Backend (`backend/app/routers/ai_intelligence.py`):
- ✅ `POST /api/ai/business-insights` genera KPIs, top sellers, `slow_movers`, alertas y tendencias usando datos reales.
- ✅ Caché en memoria configurable (`BUSINESS_INSIGHTS_CACHE_SECONDS`, default 300s). Respuestas incluyen header `X-AI-Business-Cache` (`HIT`, `MISS`, `BYPASS`).
- ⚠️ GPT-4 se usa solo si `ENABLE_AI_FEATURES=true` y existe `OPENAI_API_KEY`; caso contrario se aplican heurísticas locales.
- ⚠️ Pendiente: análitica histórica avanzada y personalización por perfil.

### Forma de uso

```json
POST /api/ai/business-insights
{
  "sales_profile_slug": "tienda-centro",
  "location_id": 2,
  "days": 45,
  "use_cache": true,
  "force_refresh": false
}
```

- Cuando `use_cache=true`, el backend reutiliza snapshots en memoria; `force_refresh=true` fuerza un recálculo.
- El frontend (`use-optimization-insights`) solicita `force_refresh` al regenerar manualmente y cae a heurísticas locales si el backend responde con error.
- Variable nueva: `BUSINESS_INSIGHTS_CACHE_SECONDS` (>=60s) controla el TTL del snapshot.

### Alternativa Actual
- Si `ENABLE_AI_FEATURES=false` o falta `OPENAI_API_KEY`, el endpoint responde con heurísticas locales (sin costo de tokens).
- El frontend sigue mostrando recomendaciones provenientes del backend (o, si este falla, activa su propio fallback local).
- Documentado como "Análisis Básico" hasta habilitar GPT-4 completo.

---

## 4. Evaluación Asistida de Trade-Ins (IA)

### Estado: ✅ **CONCEPTUALMENTE DISEÑADO** - ⚠️ **IA NO INTEGRADA**

### Descripción
Asistencia con IA para evaluar condición de dispositivos en trade-in:
- Guiar al vendedor con preguntas
- Detectar inconsistencias en evaluación
- Sugerir valor justo basado en mercado

### Componentes Implementados

#### Backend:
- ✅ Sistema de trade-ins funcional (`backend/app/routers/returns.py`)
- ✅ Políticas de evaluación (`TradeInPolicy`)
- ❌ **NO INTEGRADO**: IA para asistir evaluación

#### Frontend:
- ✅ `PendingTradeInsDialog.tsx` - Gestión de trade-ins
- ⚠️ **LIMITACIÓN**: Evaluación manual (sin sugerencias de IA)

### Implementación Futura

Podría usarse GPT-4 Vision (gpt-4-vision-preview) para:
1. Analizar fotos del dispositivo
2. Detectar daños visibles
3. Sugerir categoría de condición (Excelente/Bueno/Regular/Malo)
4. Estimar valor de mercado consultando APIs externas

**Complejidad**: Alta (requiere subida de imágenes, procesamiento de visión)
**Prioridad**: Baja (funcionalidad manual es suficiente para v1.0)

---

## 5. Resumen de Estado y Recomendaciones

### Matriz de Implementación

| Funcionalidad | Backend | Frontend | Integración | Estado General |
|--------------|---------|----------|-------------|----------------|
| Bots de Ventas | ✅ Completo | ⚠️ Parcial | ❌ N8N pendiente | **75% - Requiere N8N** |
| Forecasting | ❌ No implementado | ✅ Básico | N/A | **30% - Frontend simple** |
| Business Insights | ❌ No integrado GPT | ✅ Cálculos locales | ❌ OpenAI pendiente | **40% - Sin IA real** |
| Trade-In IA | ❌ No implementado | ✅ Manual | ❌ GPT-Vision pendiente | **20% - Concepto** |

### Recomendaciones para v1.0 Final

#### Opción A: Implementación Completa (2-3 semanas)
1. ✅ Implementar workflow N8N para bots
2. ✅ Integrar OpenAI en backend para insights
3. ✅ Crear endpoint de forecasting con algoritmo mejorado
4. ⚠️ Documentar y probar exhaustivamente

#### Opción B: MVP Realista (1 semana)
1. ✅ Completar integración N8N para bots (funcionalidad estrella)
2. ⚠️ Marcar forecasting/insights como "BETA"
3. ⚠️ Documentar claramente limitaciones
4. ✅ Deshabilitar trade-in IA (no prometido)
5. ✅ Proveer roadmap de mejoras futuras

#### Opción C: Honestidad con Cliente (Inmediato)
1. ✅ Documentar estado actual (este archivo)
2. ✅ Configurar feature flags para deshabilitar funciones incompletas
3. ✅ Proponer fase 2 del proyecto para completar IA
4. ✅ Enfocarse en pulir funcionalidades core (inventario, ventas, reportes)

---

## 6. Configuración Actual

### Para Habilitar IA (si se implementa)

```bash
# backend/.env o .env.production
ENABLE_AI_FEATURES=true
OPENAI_API_KEY=sk-tu-clave-real
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
```

### Para Deshabilitar (recomendado hasta completar)

```bash
ENABLE_AI_FEATURES=false
```

En `backend/app/main.py`, agregar middleware condicional:

```python
from app.config_production import prod_settings

if prod_settings.MAINTENANCE_MODE:
    @app.middleware("http")
    async def maintenance_mode_middleware(request: Request, call_next):
        if request.url.path.startswith("/api/ai"):
            return JSONResponse(
                status_code=503,
                content={"detail": "Funcionalidades de IA en mantenimiento"}
            )
        return await call_next(request)
```

---

## 7. Testing de IA Implementada

### Bots de Ventas (cuando N8N esté configurado)

```bash
# 1. Verificar configuración
python -c "from app.config_production import prod_settings; print('OpenAI OK' if prod_settings.OPENAI_API_KEY else 'KEY MISSING')"

# 2. Test de generación de contexto
curl -X POST http://localhost:8000/api/ai/context \
  -H "Content-Type: application/json" \
  -d '{
    "sales_profile_id": 1,
    "customer_phone": "+50499887766",
    "last_messages": ["Hola, busco un iPhone"]
  }'

# 3. Simular flujo completo
python simulate_whatsapp_flow.py
```

### Insights (si se implementa backend)

```bash
curl -X POST http://localhost:8000/api/ai/business-insights \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"location_id": 1, "date_range": 30}'
```

---

## 8. Costos Estimados de IA

### OpenAI GPT-4 Pricing (Dic 2024)

| Modelo | Input (por 1M tokens) | Output (por 1M tokens) |
|--------|----------------------|------------------------|
| GPT-4o | $2.50 | $10.00 |
| GPT-4 Turbo | $10.00 | $30.00 |
| GPT-3.5 Turbo | $0.50 | $1.50 |

### Estimación Mensual (ejemplo: 1000 conversaciones/mes)

- **Bots de Ventas**: ~$50-150/mes (dependiendo de longitud de conversaciones)
- **Business Insights**: ~$10-30/mes (1 análisis diario)
- **Total estimado**: $60-180/mes

**Recomendación**: Empezar con GPT-3.5 Turbo para reducir costos, migrar a GPT-4o si se requiere mejor calidad.

---

## 9. Conclusión

Las funcionalidades de IA del sistema están **arquitectónicamente diseñadas** y tienen **infraestructura parcial**, pero requieren:

1. **Integración con OpenAI API** (relativamente simple, ~2-3 días)
2. **Workflow N8N para bots** (crítico, ~5-7 días con testing)
3. **Algoritmos de forecasting mejorados** (opcional para v1, ~3-5 días)

### Decisión Recomendada

**Para cerrar v1.0 de forma profesional:**

- ✅ Completar bots de ventas (valor diferenciador)
- ⚠️ Documentar forecasting/insights como "simples" (sin IA avanzada)
- ✅ Deshabilitar trade-in IA (feature futura)
- ✅ Proveer este documento al cliente con roadmap claro

**Esto garantiza**:
- Honestidad sobre capacidades
- Sistema funcional y útil
- Base sólida para mejoras futuras
- Cliente informado para tomar decisiones

---

**Última actualización**: Enero 3, 2026
**Autor**: Sistema de Auditoría de Código
**Contacto**: Para preguntas sobre implementación, revisar `docs/INTEGRACION_N8N.md` y `docs/PRD.md`
