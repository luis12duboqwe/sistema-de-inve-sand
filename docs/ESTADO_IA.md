# Estado de Funcionalidades de IA

## Resumen

El sistema contempla varias funcionalidades avanzadas con Inteligencia Artificial. Este documento detalla el **estado actual de implementación** de cada una, lo que está **completo**, lo que está **en fase beta** y lo que requiere **implementación adicional**.

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
```

### Testing
```bash
# Simular flujo de WhatsApp
python simulate_whatsapp_flow.py
```

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
- ❌ **PENDIENTE**: Algoritmos avanzados (ML) o Jobs asíncronos

### Implementación Recomendada

Para producción, se recomienda:

1. **Crear endpoint de forecasting**:
```python
# backend/app/routers/analytics.py
@router.post("/api/analytics/forecast")
def generate_forecast(
    product_id: Optional[int] = None,
    location_id: Optional[int] = None,
    days_ahead: int = 90,
    db: Session = Depends(get_db)
):
    """
    Genera pronóstico de ventas usando histórico de órdenes.
    Considera estacionalidad, tendencias y eventos especiales.
    """
    # TODO: Implementar con Prophet o ARIMA
    pass
```

2. **Job asíncrono** (con Celery o APScheduler):
   - Recalcular pronósticos diariamente en segundo plano
   - Cachear resultados en Redis
   - Notificar si se detecta bajo stock inminente

3. **Mejorar algoritmo**:
   - Considerar estacionalidad (fechas especiales, fin de mes)
   - Ajustar por nuevos productos (sin histórico)
   - Integrar factores externos (promociones, competencia)

### Alternativa Actual (MVP)
Para versión inicial, usar el forecasting del frontend:
- ⚠️ Marcar como "BETA" en UI
- ⚠️ Documentar que es predicción simple (no ML avanzado)
- ⚠️ Limitar a productos con >30 días de histórico

---

## 3. Insights de Negocio (GPT-4)

### Estado: ⚠️ **FRONTEND IMPLEMENTADO - Backend Stub**

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

#### Backend:
- ❌ **NO INTEGRADO**: Llamadas a GPT-4 API
- ❌ **NO IMPLEMENTADO**: Análisis de histórico avanzado
- ❌ **NO IMPLEMENTADO**: Recomendaciones personalizadas por perfil

### Implementación Recomendada

```python
# backend/app/routers/ai_intelligence.py (extender)

@router.post("/api/ai/business-insights")
def generate_business_insights(
    location_id: Optional[int] = None,
    date_range: Optional[int] = 30,  # días
    db: Session = Depends(get_db)
):
    """
    Genera insights de negocio usando GPT-4.
    
    Análisis:
    - Productos con mayor/menor rotación
    - Oportunidades de cross-selling
    - Recomendaciones de precios
    - Alertas de stock crítico
    - Tendencias de ventas por categoría
    """
    
    # 1. Obtener métricas de base de datos
    metrics = {
        "top_sellers": [...],  # Query a orders + order_items
        "slow_movers": [...],  # Productos con pocas ventas
        "stock_alerts": [...], # Stock bajo o alto
        "revenue_trends": [...] # Ingresos por período
    }
    
    # 2. Preparar prompt para GPT-4
    prompt = f"""
    Eres un experto en gestión de inventarios. Analiza estas métricas y proporciona insights accionables:
    
    Métricas:
    {json.dumps(metrics, indent=2)}
    
    Proporciona:
    1. Top 3 acciones recomendadas
    2. Oportunidades de optimización
    3. Alertas críticas
    4. Sugerencias de precios
    """
    
    # 3. Llamar a OpenAI API
    from openai import OpenAI
    client = OpenAI(api_key=prod_settings.OPENAI_API_KEY)
    
    response = client.chat.completions.create(
        model=prod_settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Eres un experto en retail e inventarios"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5  # Más conservador para análisis
    )
    
    insights = response.choices[0].message.content
    
    # 4. Parsear y estructurar respuesta
    return {
        "generated_at": datetime.utcnow(),
        "insights": insights,
        "metrics": metrics,
        "tokens_used": response.usage.total_tokens
    }
```

### Alternativa Actual
- Frontend calcula insights simples sin IA
- Útil para MVP, pero no aprovecha potencial de GPT-4
- Considerar implementar backend o marcar como "Análisis Básico"

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

**Última actualización**: Diciembre 26, 2024
**Autor**: Sistema de Auditoría de Código
**Contacto**: Para preguntas sobre implementación, revisar `docs/INTEGRACION_N8N.md` y `docs/PRD.md`
