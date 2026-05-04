# pyright: reportAttributeAccessIssue=false, reportArgumentType=false, reportGeneralTypeIssues=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false, reportUnnecessaryComparison=false, reportDeprecated=false

from fastapi import APIRouter, Depends, HTTPException, Body, Request, Response, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any, Iterable
from datetime import UTC, datetime, timedelta
import json
import locale
import hmac
from collections import defaultdict

# Intentar configurar locale a español para fechas, fallback a default
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    pass

from app.database import get_db
from app.auth import check_permission, get_current_user_optional
from app.models import (
    SalesProfile, Product, Stock, FAQEntry, Order, OrderItem,
    Customer, AIProfileConfig, InteractionLog, TrainingQueue, Location,
    Bank, TradeInPolicy, User, ProcessedMessage
)
from app.schemas import (
    AICreateOrderRequest,
    AICreateOrderResponse,
    AICustomerResponse,
    AIConfigSchema,
    AIContextRequest,
    AIContextResponse,
    AIHandleMessageRequest,
    AIHandleMessageResponse,
    AIProfileMetric,
    AIReplyRequest,
    AIReplyResponse,
    AIStatusResponse,
    BusinessInsightRecommendation,
    BusinessInsightSlowMover,
    BusinessInsightStockAlert,
    BusinessInsightTopSeller,
    BusinessInsightTrendPoint,
    BusinessInsightsFilters,
    BusinessInsightsKPIs,
    BusinessInsightsMetrics,
    BusinessInsightsRequest,
    BusinessInsightsResponse,
    ForecastingAlertItem,
    InteractionLogCreate,
    LinkOrderRequest,
    OrderCreate,
    PaginatedResponse,
    TradeInPolicyCreate,
    TradeInPolicyResponse,
    TrainingSubmission,
    TrainingQueueItemResponse,
)
from app.services.forecasting_service import generate_sales_forecasts
from app.services.openai_service import get_openai_service
from app.services.order_service import OrderService
from app.config_production import prod_settings
from app.utils.photo_detection import (
    BOT_PHOTO_DETECTION_INSTRUCTIONS,
    detect_photo_request,
    extract_photo_request_context,
    get_response_for_photo_request,
)
from app.routers.photo_requests import create_photo_request_internal
from app.schemas.photos import PhotoRequestCreate

def _ensure_ai_features_enabled():
    if not prod_settings.ENABLE_AI_FEATURES:
        raise HTTPException(status_code=503, detail="Las funcionalidades de IA están deshabilitadas")
    return True


router = APIRouter(
    prefix="/api/ai",
    tags=["AI Intelligence"],
    dependencies=[Depends(_ensure_ai_features_enabled)],
)

_AI_RUNTIME_METRICS: Dict[str, Any] = {
    "total_messages": 0,
    "photo_handoffs": 0,
    "openai_replies": 0,
    "fallback_replies": 0,
    "duplicate_messages": 0,
    "orders_created": 0,
    "latency_ms": [],
}


def _record_latency_ms(value: float) -> None:
    latency = _AI_RUNTIME_METRICS.setdefault("latency_ms", [])
    if isinstance(latency, list):
        latency.append(max(0.0, value))
        if len(latency) > 200:
            del latency[: len(latency) - 200]


def _increment_metric(name: str) -> None:
    _AI_RUNTIME_METRICS[name] = int(_AI_RUNTIME_METRICS.get(name, 0)) + 1

def _normalize_phone(phone: str) -> str:
    digits = "".join(filter(str.isdigit, phone or ""))
    return digits or phone


def _extract_search_keywords(message: str) -> List[str]:
    stop_words = {
        'hola', 'quiero', 'tienes', 'precio', 'cuanto', 'cuesta', 'busco', 'necesito', 'para', 'celular', 'telefono',
        'fotos', 'foto', 'imagen', 'imagenes', 'gris', 'negro', 'blanco', 'azul', 'rojo', 'verde', 'muestrame', 'mostrar',
    }
    return [w.lower() for w in message.split() if len(w) >= 2 and w.lower() not in stop_words]


def _parse_customer_memory(customer: Customer) -> Dict[str, Any]:
    raw = (customer.ai_memory_json or "").strip()
    if not raw:
        return {
            "preferred_brands": [],
            "mentioned_products": [],
            "requested_colors": [],
            "requested_variants": [],
            "semantic_notes": [],
            "last_intent": None,
        }
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except (TypeError, json.JSONDecodeError):
        pass
    return {
        "preferred_brands": [],
        "mentioned_products": [],
        "requested_colors": [],
        "requested_variants": [],
        "semantic_notes": [],
        "last_intent": None,
    }


def _save_customer_memory(customer: Customer, memory: Dict[str, Any]) -> None:
    customer.ai_memory_json = json.dumps(memory, ensure_ascii=False)
    customer.memory_updated_at = datetime.now(UTC)


def _infer_customer_intent(message: str) -> str:
    text = message.lower()
    if any(term in text for term in ["foto", "fotos", "imagen", "muéstrame", "muestrame", "show me"]):
        return "photo_request"
    if any(term in text for term in ["cuotas", "financiamiento", "tarjeta", "prima"]):
        return "financing"
    if any(term in text for term in ["precio", "cuesta", "valor"]):
        return "pricing"
    if any(term in text for term in ["tienes", "hay", "disponible", "stock"]):
        return "availability"
    return "general"


def _find_candidate_products(
    db: Session,
    message: str,
    customer: Optional[Customer] = None,
    limit: int = 5,
) -> List[Product]:
    search_text = message
    if customer and customer.last_referenced_product_name:
        lowered = message.lower()
        if any(token in lowered for token in ["gris", "negro", "blanco", "ese", "esa", "este", "fotos", "foto", "imagen"]):
            search_text = f"{message} {customer.last_referenced_product_name}"

    keywords = _extract_search_keywords(search_text)
    if not keywords and customer and customer.last_referenced_product_name:
        keywords = _extract_search_keywords(customer.last_referenced_product_name)

    if not keywords:
        return []

    and_conditions = []
    for keyword in keywords[:6]:
        and_conditions.append(
            or_(
                Product.nombre.ilike(f"%{keyword}%"),
                Product.marca.ilike(f"%{keyword}%"),
                Product.modelo.ilike(f"%{keyword}%"),
                Product.sku.ilike(f"%{keyword}%"),
                Product.categoria.ilike(f"%{keyword}%"),
            )
        )

    candidates = db.query(Product).options(
        joinedload(Product.stock_items).joinedload(Stock.location)
    ).filter(Product.activo == True, *and_conditions).limit(limit).all()

    if candidates:
        return candidates

    or_conditions = []
    for keyword in keywords[:6]:
        or_conditions.extend([
            Product.nombre.ilike(f"%{keyword}%"),
            Product.marca.ilike(f"%{keyword}%"),
            Product.modelo.ilike(f"%{keyword}%"),
            Product.sku.ilike(f"%{keyword}%"),
        ])

    return db.query(Product).options(
        joinedload(Product.stock_items).joinedload(Stock.location)
    ).filter(Product.activo == True, or_(*or_conditions)).limit(limit).all()


def _retrieve_semantic_memory_snippets(db: Session, customer_id: int, message: str, limit: int = 3) -> List[str]:
    keywords = set(_extract_search_keywords(message))
    if not keywords:
        return []

    logs = db.query(InteractionLog).filter(
        InteractionLog.customer_id == customer_id
    ).order_by(InteractionLog.created_at.desc()).limit(40).all()

    scored: List[tuple[int, str]] = []
    for log in logs:
        content = (log.content or "").strip()
        if not content:
            continue
        content_keywords = set(_extract_search_keywords(content))
        overlap = len(keywords.intersection(content_keywords))
        if overlap > 0:
            scored.append((overlap, f"{log.role}: {content[:180]}"))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [snippet for _, snippet in scored[:limit]]


def _build_customer_memory_summary(customer: Customer, memory: Dict[str, Any]) -> str:
    mentioned = memory.get("mentioned_products") or []
    preferred_brands = memory.get("preferred_brands") or []
    requested_colors = memory.get("requested_colors") or []
    semantic_notes = memory.get("semantic_notes") or []

    parts: List[str] = []
    if customer.conversation_summary:
        parts.append(f"Resumen: {customer.conversation_summary}")
    if preferred_brands:
        parts.append(f"Marcas preferidas: {', '.join(preferred_brands[-3:])}")
    if requested_colors:
        parts.append(f"Colores vistos: {', '.join(requested_colors[-3:])}")
    if mentioned:
        latest_products = [str(item.get('name')) for item in mentioned[-3:] if item.get('name')]
        if latest_products:
            parts.append(f"Productos mencionados: {', '.join(latest_products)}")
    if semantic_notes:
        parts.append(f"Notas relevantes: {' | '.join(str(note) for note in semantic_notes[-3:])}")
    return "\n".join(parts)


def _update_customer_memory(
    db: Session,
    customer: Customer,
    message: str,
    matched_products: Optional[List[Product]] = None,
    bot_reply: Optional[str] = None,
    color_requested: Optional[str] = None,
    size_requested: Optional[str] = None,
) -> None:
    memory = _parse_customer_memory(customer)
    matched_products = matched_products or []

    preferred_brands = list(memory.get("preferred_brands") or [])
    mentioned_products = list(memory.get("mentioned_products") or [])
    requested_colors = list(memory.get("requested_colors") or [])
    requested_variants = list(memory.get("requested_variants") or [])
    semantic_notes = list(memory.get("semantic_notes") or [])

    for product in matched_products[:2]:
        product_name = str(product.nombre)
        product_brand = str(product.marca or "").strip()
        product_payload = {
            "id": int(product.id),
            "name": product_name,
            "brand": product_brand,
            "at": datetime.now(UTC).isoformat(),
        }
        mentioned_products = [item for item in mentioned_products if item.get("id") != product_payload["id"]]
        mentioned_products.append(product_payload)
        customer.last_referenced_product_id = int(product.id)
        customer.last_referenced_product_name = product_name
        if product_brand and product_brand not in preferred_brands:
            preferred_brands.append(product_brand)

    if color_requested:
        customer.last_referenced_color = color_requested
        if color_requested not in requested_colors:
            requested_colors.append(color_requested)

    if size_requested:
        customer.last_referenced_variant = size_requested
        if size_requested not in requested_variants:
            requested_variants.append(size_requested)

    inferred_intent = _infer_customer_intent(message)
    memory["last_intent"] = inferred_intent
    memory["preferred_brands"] = preferred_brands[-5:]
    memory["mentioned_products"] = mentioned_products[-5:]
    memory["requested_colors"] = requested_colors[-5:]
    memory["requested_variants"] = requested_variants[-5:]

    summary_parts = [
        f"Última intención: {inferred_intent}",
    ]
    if customer.last_referenced_product_name:
        summary_parts.append(f"Último producto: {customer.last_referenced_product_name}")
    if customer.last_referenced_color:
        summary_parts.append(f"Color de interés: {customer.last_referenced_color}")
    if customer.last_referenced_variant:
        summary_parts.append(f"Variante: {customer.last_referenced_variant}")

    semantic_note = f"Cliente preguntó: {message[:120]}"
    if bot_reply:
        semantic_note += f" | Bot respondió: {bot_reply[:120]}"
    semantic_notes.append(semantic_note)
    memory["semantic_notes"] = semantic_notes[-6:]

    customer.conversation_summary = " | ".join(summary_parts)
    customer.last_interaction_at = datetime.now(UTC)
    _save_customer_memory(customer, memory)
    db.add(customer)


def _infer_channel_from_sales_profile(profile: SalesProfile) -> str:
    raw_channels = (profile.canales or "").strip()
    if not raw_channels:
        return "whatsapp"

    try:
        parsed = json.loads(raw_channels)
        if isinstance(parsed, list) and parsed:
            first = str(parsed[0]).strip().lower()
            return "messenger" if first == "facebook" else first
    except (TypeError, json.JSONDecodeError):
        pass

    first = raw_channels.split(",")[0].strip().lower()
    return "messenger" if first == "facebook" else (first or "whatsapp")


def _find_product_name_hint(db: Session, message: str) -> str:
    candidates = _find_candidate_products(db, message, None, limit=1)
    if candidates and candidates[0].nombre:
        return str(candidates[0].nombre)

    return "Producto solicitado"


def _compose_ai_messages(
    context: AIContextResponse,
    user_message: str,
    override_history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    def _truncate(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...[truncated]"

    inventory = _truncate(context.relevant_inventory or "", 3500)
    faqs = _truncate(context.relevant_faqs or "", 2000)
    financing = _truncate(context.financing_info or "", 1800)

    knowledge_blocks = "\n\n".join(
        [
            "INVENTARIO DISPONIBLE:\n" + inventory,
            "FAQ RELEVANTES:\n" + faqs,
            "FINANCIAMIENTO Y POLITICAS:\n" + financing,
        ]
    )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": context.system_prompt},
        {"role": "system", "content": knowledge_blocks},
    ]

    history = override_history if override_history is not None else context.previous_context
    if history:
        compact_history: List[Dict[str, str]] = []
        for item in history[-6:]:
            role = str(item.get("role") or "user")
            content = str(item.get("content") or "")
            compact_history.append({"role": role, "content": content[:280]})
        messages.extend(compact_history)

    messages.append({"role": "user", "content": user_message})
    return messages


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _isoformat(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.isoformat()


def _ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_ai_business_response(raw_text: str) -> Dict[str, Any]:
    if not raw_text:
        return {}
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw_text[start : end + 1])
            except json.JSONDecodeError:
                return {}
    return {}


def _build_fallback_recommendations(metrics: Dict[str, Any]) -> List[BusinessInsightRecommendation]:
    recommendations: List[BusinessInsightRecommendation] = []
    stock_alerts: List[Dict[str, Any]] = metrics.get("stock_alerts") or []
    slow_movers: List[Dict[str, Any]] = metrics.get("slow_movers") or []
    top_sellers: List[Dict[str, Any]] = metrics.get("top_sellers") or []

    if stock_alerts:
        alert = stock_alerts[0]
        recommendations.append(
            BusinessInsightRecommendation(
                title="Reponer stock crítico",
                action=f"Reordena {alert.get('product_name')} para cubrir al menos 2 semanas de demanda.",
                impact=f"Stock restante: {alert.get('stock_available')} uds | Proyección {round(_safe_float(alert.get('days_until_stockout')), 1)} días",
                category="inventario",
                priority="alta",
            )
        )

    if slow_movers:
        slow = slow_movers[0]
        recommendations.append(
            BusinessInsightRecommendation(
                title="Liquidar inventario lento",
                action=f"Aplica bundle o descuento táctico para {slow.get('product_name')} y libera capital inmovilizado.",
                impact=f"{slow.get('stock_available')} uds sin rotación hace {slow.get('days_without_sales')} días",
                category="ventas",
                priority="media",
            )
        )

    if top_sellers:
        top = top_sellers[0]
        recommendations.append(
            BusinessInsightRecommendation(
                title="Potenciar producto estrella",
                action=f"Garantiza stock y campañas de upsell para {top.get('product_name')}.",
                impact=f"Ingresos últimos {round(_safe_float(top.get('revenue')), 2)} | Margen {round(_safe_float(top.get('gross_profit')), 2)}",
                category="crecimiento",
                priority="media",
            )
        )

    if not recommendations:
        recommendations.append(
            BusinessInsightRecommendation(
                title="Revisar estrategia",
                action="Sin datos suficientes: valida captura de ventas e inventario antes de generar insights.",
                category="operaciones",
                priority="media",
            )
        )

    return recommendations[:5]


openai_service = get_openai_service()

_BUSINESS_INSIGHTS_CACHE_MAX_ENTRIES = 64


def _get_configured_ai_service_tokens() -> List[str]:
    tokens: List[str] = []
    if getattr(prod_settings, "N8N_AUTH_TOKEN", ""):
        tokens.append(prod_settings.N8N_AUTH_TOKEN)
    return [token for token in tokens if token]


def _is_valid_ai_service_token(request: Request) -> bool:
    configured_tokens = _get_configured_ai_service_tokens()
    if not configured_tokens:
        return False

    presented_token = (
        request.headers.get("X-AI-Service-Token")
        or request.headers.get("X-N8N-Token")
    )
    if not presented_token:
        authorization = request.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            presented_token = authorization[7:].strip()

    if not presented_token:
        return False

    return any(hmac.compare_digest(presented_token, valid_token) for valid_token in configured_tokens)


def _require_ai_integration_auth(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if current_user and current_user.is_active:
        return current_user

    if _is_valid_ai_service_token(request):
        return None

    raise HTTPException(
        status_code=401,
        detail="AI integration authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _get_business_insights_cache(request: Request) -> Dict[str, Any]:
    cache = getattr(request.app.state, "business_insights_cache", None)
    if cache is None:
        cache = {}
        request.app.state.business_insights_cache = cache
    return cache


def _business_insights_cache_ttl() -> int:
    try:
        ttl = int(getattr(prod_settings, "BUSINESS_INSIGHTS_CACHE_SECONDS", 300))
    except (TypeError, ValueError):
        ttl = 300
    return max(60, ttl)


def _utcnow() -> datetime:
    """Return timezone-aware UTC timestamps for AI endpoints."""
    return datetime.now(UTC)


def _build_local_fallback_reply(context: AIContextResponse, user_message: str) -> str:
    message_lower = (user_message or "").lower()
    if any(token in message_lower for token in ["precio", "cuanto", "valor"]):
        return "Estoy teniendo una demora técnica momentánea. Mientras tanto, te comparto precios y stock disponibles en un momento; ¿me confirmas el modelo exacto y color que buscas?"
    if any(token in message_lower for token in ["cuotas", "financiamiento", "tarjeta"]):
        return "Ahora mismo tengo una intermitencia técnica, pero sí manejamos opciones con tarjeta y cuotas. Si me dices el producto, te calculo una cuota aproximada de inmediato."
    if any(token in message_lower for token in ["foto", "fotos", "imagen"]):
        return get_response_for_photo_request(language="es")
    return "Estoy presentando una demora técnica breve. Ya retomamos en segundos; si quieres, te ayudo de una vez con disponibilidad, precio y cuotas del modelo que te interesa."


def _cleanup_processed_messages(db: Session) -> None:
    now = _utcnow()
    db.query(ProcessedMessage).filter(ProcessedMessage.expires_at <= now).delete(synchronize_session=False)


def _mark_message_processed(
    db: Session,
    message_id: str,
    channel: str,
    customer_phone: str,
    sales_profile_id: Optional[int],
    ttl_hours: int = 24,
) -> bool:
    if not message_id.strip():
        return True

    now = _utcnow()
    existing = db.query(ProcessedMessage).filter(
        ProcessedMessage.message_id == message_id,
        ProcessedMessage.expires_at > now,
    ).first()
    if existing:
        return False

    entry = ProcessedMessage(
        message_id=message_id,
        channel=channel,
        customer_phone=customer_phone,
        sales_profile_id=sales_profile_id,
        expires_at=now + timedelta(hours=max(1, ttl_hours)),
    )
    db.add(entry)
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def _make_business_insights_cache_key(days: int, payload: BusinessInsightsRequest) -> str:
    return json.dumps(
        {
            "days": days,
            "location_id": payload.location_id,
            "sales_profile_id": payload.sales_profile_id,
            "sales_profile_slug": payload.sales_profile_slug,
        },
        sort_keys=True,
        default=str,
    )


def _cleanup_business_insights_cache(cache: Dict[str, Any]) -> None:
    now = _utcnow()
    expired = [key for key, entry in cache.items() if entry.get("expires_at") <= now]
    for key in expired:
        cache.pop(key, None)

    while len(cache) > _BUSINESS_INSIGHTS_CACHE_MAX_ENTRIES:
        cache.pop(next(iter(cache)))

# --- Endpoints ---

@router.get("/config/{sales_profile_id}", response_model=AIConfigSchema)
def get_ai_config(
    sales_profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:view"))
):
    """Obtiene la configuración de IA para un perfil específico"""
    config = db.query(AIProfileConfig).filter(AIProfileConfig.sales_profile_id == sales_profile_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="AI Config not found")
    return config

@router.post("/config/{sales_profile_id}", response_model=AIConfigSchema)
def update_ai_config(
    sales_profile_id: int, 
    config: AIConfigSchema, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:edit"))
):
    """Crea o actualiza la configuración de IA para un perfil"""
    # Verify profile exists
    profile = db.query(SalesProfile).filter(SalesProfile.id == sales_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Sales Profile not found")

    db_config = db.query(AIProfileConfig).filter(AIProfileConfig.sales_profile_id == sales_profile_id).first()
    
    if not db_config:
        db_config = AIProfileConfig(sales_profile_id=sales_profile_id)
        db.add(db_config)
    
    db_config.model_name = config.model_name
    db_config.temperature = config.temperature
    db_config.system_prompt = config.system_prompt
    db_config.initial_greeting = config.initial_greeting
    db_config.voice_tone = config.voice_tone
    db_config.context_rules = config.context_rules
    db_config.is_active = config.is_active
    db_config.admin_notification_phone = config.admin_notification_phone
    
    # V2.2
    db_config.business_description = config.business_description
    db_config.sales_goal = config.sales_goal
    db_config.negotiation_style = config.negotiation_style
    db_config.max_discount_rate = config.max_discount_rate
    db_config.fallback_human_trigger = config.fallback_human_trigger
    
    db.commit()
    db.refresh(db_config)
    return db_config


@router.get("/status", response_model=AIStatusResponse)
def get_ai_status(
    alerts_limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """Consolida métricas operativas de los bots IA y alertas de pronósticos."""
    now = _utcnow()
    last_24h = now - timedelta(hours=24)
    last_7_days = now - timedelta(days=7)
    alerts_limit = max(1, min(alerts_limit, 20))

    def _rows_to_int_map(rows: Iterable[tuple[Optional[int], Any]]) -> Dict[int, int]:
        metrics = {}
        for profile_id, value in rows:
            if profile_id is None:
                continue
            metrics[int(profile_id)] = int(value or 0)
        return metrics

    profiles = db.query(SalesProfile).options(joinedload(SalesProfile.ai_config)).all()
    total_profiles = len(profiles)

    interaction_counts_24 = _rows_to_int_map(
        db.query(InteractionLog.sales_profile_id, func.count(InteractionLog.id))
        .filter(InteractionLog.created_at >= last_24h)
        .group_by(InteractionLog.sales_profile_id)
        .all()
    )

    interaction_counts_7 = _rows_to_int_map(
        db.query(InteractionLog.sales_profile_id, func.count(InteractionLog.id))
        .filter(InteractionLog.created_at >= last_7_days)
        .group_by(InteractionLog.sales_profile_id)
        .all()
    )

    token_counts_24 = _rows_to_int_map(
        db.query(InteractionLog.sales_profile_id, func.sum(InteractionLog.tokens_used))
        .filter(InteractionLog.created_at >= last_24h)
        .group_by(InteractionLog.sales_profile_id)
        .all()
    )

    token_counts_7 = _rows_to_int_map(
        db.query(InteractionLog.sales_profile_id, func.sum(InteractionLog.tokens_used))
        .filter(InteractionLog.created_at >= last_7_days)
        .group_by(InteractionLog.sales_profile_id)
        .all()
    )

    last_interaction_map = {
        pid: last_at
        for pid, last_at in db.query(
            InteractionLog.sales_profile_id, func.max(InteractionLog.created_at)
        )
        .group_by(InteractionLog.sales_profile_id)
        .all()
        if pid is not None
    }

    training_rows = (
        db.query(TrainingQueue.sales_profile_id, func.count(TrainingQueue.id))
        .filter(TrainingQueue.status == "pending")
        .group_by(TrainingQueue.sales_profile_id)
        .all()
    )
    training_pending_map = {}
    training_backlog = 0
    for profile_id, count in training_rows:
        clean_count = int(count or 0)
        training_backlog += clean_count
        if profile_id is not None:
            training_pending_map[int(profile_id)] = clean_count

    customers_flagged = (
        db.query(func.count(Customer.id))
        .filter(or_(Customer.is_troll == True, Customer.is_blocked == True))
        .scalar()
        or 0
    )

    interactions_last_24h = sum(interaction_counts_24.values())
    tokens_last_24h = sum(token_counts_24.values())
    avg_tokens_per_response = (
        tokens_last_24h / interactions_last_24h if interactions_last_24h else 0.0
    )

    profile_metrics: List[AIProfileMetric] = []
    active_profiles = 0
    inactive_profiles = 0

    for profile in profiles:
        profile_id = int(profile.id)
        is_ai_active = bool(profile.ai_config and profile.ai_config.is_active)
        if is_ai_active:
            active_profiles += 1
        else:
            inactive_profiles += 1

        profile_metrics.append(
            AIProfileMetric(
                sales_profile_id=profile_id,
                sales_profile_name=profile.name,
                slug=profile.slug,
                is_ai_active=is_ai_active,
                last_interaction_at=last_interaction_map.get(profile_id),
                interactions_last_7_days=interaction_counts_7.get(profile_id, 0),
                tokens_last_7_days=token_counts_7.get(profile_id, 0),
                pending_training_items=training_pending_map.get(profile_id, 0),
            )
        )

    profile_metrics.sort(key=lambda metric: metric.interactions_last_7_days, reverse=True)

    forecasts = generate_sales_forecasts(db)
    forecasting_alerts: List[ForecastingAlertItem] = []

    for forecast in forecasts:
        if forecast.restock_recommendation <= 0 and forecast.days_until_stockout > 10:
            continue
        forecasting_alerts.append(
            ForecastingAlertItem(
                product_id=forecast.product_id,
                product_name=forecast.product_name,
                days_until_stockout=forecast.days_until_stockout,
                restock_recommendation=forecast.restock_recommendation,
                trend=forecast.trend,
            )
        )
        if len(forecasting_alerts) >= alerts_limit:
            break

    if not forecasting_alerts:
        for forecast in forecasts[:alerts_limit]:
            forecasting_alerts.append(
                ForecastingAlertItem(
                    product_id=forecast.product_id,
                    product_name=forecast.product_name,
                    days_until_stockout=forecast.days_until_stockout,
                    restock_recommendation=forecast.restock_recommendation,
                    trend=forecast.trend,
                )
            )
            if len(forecasting_alerts) >= alerts_limit:
                break

    return AIStatusResponse(
        snapshot_generated_at=now,
        total_sales_profiles=total_profiles,
        ai_profiles_active=active_profiles,
        ai_profiles_inactive=inactive_profiles,
        interactions_last_24h=interactions_last_24h,
        tokens_last_24h=tokens_last_24h,
        avg_tokens_per_response=round(avg_tokens_per_response, 2),
        customers_flagged=int(customers_flagged),
        training_backlog=training_backlog,
        ai_profiles=profile_metrics,
        forecasting_alerts=forecasting_alerts,
    )


@router.post("/business-insights", response_model=BusinessInsightsResponse)
def generate_business_insights(
    payload: BusinessInsightsRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view")),
):
    """Genera insights de negocio usando métricas locales y (opcional) GPT-4."""
    days = max(7, min(payload.days, 120))
    now = _utcnow()
    period_start = now - timedelta(days=days)

    cache_store = _get_business_insights_cache(request)
    cache_key = _make_business_insights_cache_key(days, payload)
    cache_entry = cache_store.get(cache_key) if payload.use_cache and not payload.force_refresh else None
    if cache_entry and cache_entry.get("expires_at") and cache_entry["expires_at"] > now:
        response.headers["X-AI-Business-Cache"] = "HIT"
        cached_value = cache_entry.get("value")
        if isinstance(cached_value, BusinessInsightsResponse):
            return cached_value.model_copy(deep=True)
        return cached_value

    sales_profile_id = payload.sales_profile_id
    if payload.sales_profile_slug:
        profile = db.query(SalesProfile).filter(SalesProfile.slug == payload.sales_profile_slug).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Sales Profile not found")
        sales_profile_id = profile.id
    elif sales_profile_id:
        profile = db.query(SalesProfile).filter(SalesProfile.id == sales_profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Sales Profile not found")

    if payload.location_id:
        location_exists = db.query(Location).filter(Location.id == payload.location_id).first()
        if not location_exists:
            raise HTTPException(status_code=404, detail="Location not found")

    orders_query = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.created_at >= period_start)
        .filter(Order.estado != "cancelada")
    )
    if sales_profile_id:
        orders_query = orders_query.filter(Order.sales_profile_id == sales_profile_id)
    if payload.location_id:
        orders_query = orders_query.filter(Order.source_location_id == payload.location_id)

    orders = orders_query.all()

    sales_map: Dict[int, Dict[str, Any]] = {}
    daily_revenue = defaultdict(float)
    total_revenue = 0.0
    gross_profit_total = 0.0

    for order in orders:
        order_total = _safe_float(order.total)
        total_revenue += order_total
        order_created_at = _ensure_aware(order.created_at)
        if order_created_at:
            daily_key = order_created_at.date().isoformat()
            daily_revenue[daily_key] += order_total
        for item in order.items:
            product = item.product
            if not product:
                continue
            entry = sales_map.setdefault(
                product.id,
                {
                    "product_name": product.nombre,
                    "units_sold": 0,
                    "revenue": 0.0,
                    "gross_profit": 0.0,
                    "last_sale_at": None,
                },
            )
            entry["units_sold"] += item.cantidad
            item_revenue = _safe_float(item.precio_unitario) * item.cantidad
            entry["revenue"] += item_revenue
            item_cost = _safe_float(product.costo) * item.cantidad
            profit = item_revenue - item_cost
            entry["gross_profit"] += profit
            gross_profit_total += profit
            if order_created_at:
                last_sale_at = entry.get("last_sale_at")
                if not last_sale_at or order_created_at > last_sale_at:
                    entry["last_sale_at"] = order_created_at

    orders_count = len(orders)
    avg_order_value = total_revenue / orders_count if orders_count else 0.0

    products = (
        db.query(Product)
        .options(joinedload(Product.stock_items).joinedload(Stock.location))
        .filter(Product.activo == True)
        .all()
    )

    top_sellers = [
        {
            "product_id": product_id,
            "product_name": data["product_name"],
            "units_sold": data["units_sold"],
            "revenue": round(data["revenue"], 2),
            "gross_profit": round(data["gross_profit"], 2),
        }
        for product_id, data in sales_map.items()
        if data["units_sold"] > 0
    ]
    top_sellers.sort(key=lambda item: item["revenue"], reverse=True)
    top_sellers = top_sellers[:5]

    slow_movers: List[Dict[str, Any]] = []
    stock_alerts: List[Dict[str, Any]] = []

    for product in products:
        stock_available = 0
        for stock in product.stock_items:
            if payload.location_id and stock.location_id != payload.location_id:
                continue
            available = max(0, (stock.cantidad_disponible or 0) - (stock.cantidad_reservada or 0))
            stock_available += available

        if stock_available <= 0:
            continue

        sale_info = sales_map.get(product.id)
        last_sale_at: Optional[datetime] = sale_info.get("last_sale_at") if sale_info else None
        days_without_sales = (now - last_sale_at).days if last_sale_at else days + 30
        units_sold = sale_info["units_sold"] if sale_info else 0

        if units_sold == 0 or days_without_sales > max(14, days // 2):
            slow_movers.append(
                {
                    "product_id": product.id,
                    "product_name": product.nombre,
                    "stock_available": stock_available,
                    "days_without_sales": int(days_without_sales),
                    "last_sale_at": _isoformat(last_sale_at),
                }
            )

        avg_daily_demand = (sale_info["units_sold"] / days) if sale_info and days else 0.0
        days_until_stockout = (stock_available / avg_daily_demand) if avg_daily_demand > 0 else None
        if avg_daily_demand > 0 and stock_available < max(5, avg_daily_demand * 5):
            stock_alerts.append(
                {
                    "product_id": product.id,
                    "product_name": product.nombre,
                    "stock_available": stock_available,
                    "avg_daily_demand": round(avg_daily_demand, 2),
                    "days_until_stockout": round(days_until_stockout, 1) if days_until_stockout else None,
                }
            )

    slow_movers.sort(key=lambda item: (item["days_without_sales"], item["stock_available"]), reverse=True)
    slow_movers = slow_movers[:5]

    stock_alerts.sort(key=lambda item: item["days_until_stockout"] if item["days_until_stockout"] is not None else 9999)
    stock_alerts = stock_alerts[:5]

    revenue_trends = [
        {"date": date_key, "revenue": round(value, 2)}
        for date_key, value in sorted(daily_revenue.items())
    ]
    revenue_trends = revenue_trends[-14:]

    metrics_model = BusinessInsightsMetrics(
        kpis=BusinessInsightsKPIs(
            total_revenue=round(total_revenue, 2),
            orders_count=orders_count,
            avg_order_value=round(avg_order_value, 2),
            gross_margin_estimate=round(gross_profit_total, 2),
        ),
        top_sellers=[BusinessInsightTopSeller(**item) for item in top_sellers],
        slow_movers=[BusinessInsightSlowMover(**item) for item in slow_movers],
        stock_alerts=[BusinessInsightStockAlert(**item) for item in stock_alerts],
        revenue_trends=[BusinessInsightTrendPoint(**item) for item in revenue_trends],
    )

    recommendations: List[BusinessInsightRecommendation] = []
    ai_summary: Optional[str] = None
    tokens_used = 0
    raw_response: Optional[str] = None

    metrics_payload = metrics_model.model_dump()

    if prod_settings.ENABLE_AI_FEATURES and prod_settings.OPENAI_API_KEY:
        try:
            metrics_json = json.dumps(metrics_payload, ensure_ascii=False)
            prompt = (
                "Analiza el siguiente JSON de métricas (periodo de "
                f"{days} días) y devuelve recomendaciones accionables.\n"
                "Responde ÚNICAMENTE en JSON con el formato:\n"
                "{\n"
                "  \"summary\": \"...\",\n"
                "  \"recommendations\": [\n"
                "    {\n"
                "      \"title\": \"\",\n"
                "      \"action\": \"\",\n"
                "      \"impact\": \"\",\n"
                "      \"category\": \"inventario|ventas|operaciones|finanzas\",\n"
                "      \"priority\": \"alta|media|baja|critica\"\n"
                "    }\n"
                "  ]\n"
                "}\n"
                f"Contexto:\n{metrics_json}"
            )

            completion = openai_service.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un analista de retail que entrega planes concretos basados en datos.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model=prod_settings.OPENAI_MODEL,
                temperature=0.4,
            )

            raw_response = completion.get("reply") or ""
            tokens_used = int((completion.get("usage") or {}).get("total_tokens") or 0)
            parsed = _parse_ai_business_response(raw_response)
            ai_summary = parsed.get("summary")
            for rec in parsed.get("recommendations", []) or []:
                action = rec.get("action") or rec.get("recommendation")
                title = rec.get("title") or rec.get("headline") or action or "Recomendación"
                priority = (rec.get("priority") or "media").lower()
                if priority not in {"alta", "media", "baja", "critica"}:
                    priority = "media"
                recommendations.append(
                    BusinessInsightRecommendation(
                        title=title,
                        action=action or title,
                        impact=rec.get("impact"),
                        category=rec.get("category"),
                        priority=priority, 
                    )
                )
        except RuntimeError as exc:
            # Log y continuar con heurísticas
            print(f"AI Business Insights error: {exc}")

    if not recommendations:
        recommendations = _build_fallback_recommendations(metrics_payload)
        if not ai_summary:
            ai_summary = "Se generaron recomendaciones basadas en heurísticas locales."
    result = BusinessInsightsResponse(
        generated_at=_utcnow(),
        period_days=days,
        filters=BusinessInsightsFilters(
            location_id=payload.location_id,
            sales_profile_id=sales_profile_id,
            sales_profile_slug=payload.sales_profile_slug,
        ),
        metrics=metrics_model,
        recommendations=recommendations,
        ai_summary=ai_summary,
        tokens_used=tokens_used,
        raw_response=raw_response,
    )

    if payload.use_cache:
        _cleanup_business_insights_cache(cache_store)
        cache_store[cache_key] = {
            "expires_at": _utcnow() + timedelta(seconds=_business_insights_cache_ttl()),
            "value": result.model_copy(deep=True),
        }
        response.headers.setdefault("X-AI-Business-Cache", "MISS")
    else:
        response.headers.setdefault("X-AI-Business-Cache", "BYPASS")

    return result

@router.post("/context", response_model=AIContextResponse)
def get_ai_context(
    request: AIContextRequest,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(_require_ai_integration_auth),
):
    """
    El CEREBRO: Recibe un mensaje y devuelve todo lo necesario para que GPT responda.
    1. Identifica/Crea al cliente.
    2. Busca la configuración del Bot.
    3. Busca inventario y FAQs relevantes.
    """
    # 1. Validar Perfil de Venta
    profile = db.query(SalesProfile).filter(SalesProfile.slug == request.sales_profile_slug).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Sales Profile not found")
    
    # V2.3: Extraer Tasa de Cambio y Configuración del Perfil
    exchange_rate = 25.0 # Default fallback
    try:
        if profile.configuracion:
            profile_config = json.loads(profile.configuracion)
            exchange_rate = float(profile_config.get('exchange_rate', 25.0))
    except Exception as e:
        print(f"Error parsing profile config: {e}")

    # 2. Obtener Configuración de IA
    ai_config = db.query(AIProfileConfig).filter(AIProfileConfig.sales_profile_id == profile.id).first()
    
    # Prompt por defecto robusto
    default_system_prompt = """Eres un asistente de ventas experto y amable para una tienda de celulares.
    Tu objetivo es ayudar al cliente a encontrar el producto ideal y cerrar la venta.
    
    DIRECTRICES PRINCIPALES:
    1. Usa SIEMPRE la información del INVENTARIO proporcionado. No inventes productos ni precios.
    2. Si el producto no está en la lista, di que no lo tienes disponible por el momento.
    3. Para preguntas frecuentes, usa la sección de FAQs.
    4. Sé conciso y directo, usa emojis moderadamente para ser amigable.
    5. Si el cliente pregunta por financiamiento, explica las opciones disponibles claramente.
    """

    if not ai_config:
        # Configuración Default si no existe
        ai_config = AIProfileConfig(
            system_prompt=default_system_prompt,
            model_name="gpt-3.5-turbo",
            temperature=0.7
        )
    
    # 3. Gestión de Cliente (Get or Create)
    # V2.5: Normalizar teléfono (eliminar espacios, guiones, paréntesis)
    normalized_phone = "".join(filter(str.isdigit, request.customer_phone))
    # Si empieza con 504 (Honduras), dejarlo, si no, ver si es necesario. 
    # Por ahora solo limpiamos caracteres no numéricos.
    
    customer = db.query(Customer).filter(Customer.phone_number == normalized_phone).first()
    if not customer:
        # Fallback: intentar buscar con el formato original por si acaso
        customer = db.query(Customer).filter(Customer.phone_number == request.customer_phone).first()
        
    if not customer:
        try:
            customer = Customer(
                phone_number=normalized_phone,
                name=request.customer_name,
                reputation_score=100
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
        except IntegrityError:
            db.rollback()
            # Race condition: created by another request in the meantime
            customer = db.query(Customer).filter(Customer.phone_number == normalized_phone).first()
            if not customer:
                raise HTTPException(status_code=500, detail="Error creating customer")
    else:
        # Actualizar nombre si viene nuevo
        if request.customer_name and not customer.name:
            customer.name = request.customer_name
            db.commit()
            
    # Verificar si es Troll
    if customer.is_blocked:
        raise HTTPException(status_code=403, detail="Customer is blocked")
        
    # Si es troll pero no bloqueado, inyectar instrucción de comportamiento
    troll_instruction = ""
    if customer.is_troll:
        troll_instruction = "\n[MODO TROLL DETECTADO]: Este usuario ha sido marcado como problemático. Sé extremadamente cortante, directo y no ofrezcas descuentos ni pierdas tiempo. Responde solo lo estrictamente necesario."
    elif customer.reputation_score < 50:
        troll_instruction = "\n[ADVERTENCIA DE REPUTACIÓN]: Este cliente tiene baja reputación. Sé cauteloso, recuerda que NO damos crédito bajo ninguna circunstancia. Mantén la conversación estrictamente profesional."

    memory = _parse_customer_memory(customer)
    semantic_memories = _retrieve_semantic_memory_snippets(db, int(customer.id), request.message_content)
    memory_hint = _build_customer_memory_summary(customer, memory)

    search_message = request.message_content
    if customer.last_referenced_product_name and any(
        token in request.message_content.lower()
        for token in ["foto", "fotos", "imagen", "ese", "esa", "este", "gris", "negro", "blanco", "color"]
    ):
        search_message = f"{request.message_content} {customer.last_referenced_product_name}"

    # 4. Obtener Inventario Relevante (Búsqueda Híbrida Mejorada)
    # Estrategia de Embudo: 
    # 1. Búsqueda Estricta (AND): Debe coincidir con TODAS las palabras clave (ej: "iPhone" AND "13")
    # 2. Búsqueda Relajada (OR): Si hay pocos resultados, buscar coincidencias parciales
    
    relevant_products = []
    # Filtrar palabras cortas y comunes para evitar ruido
    stop_words = {'hola', 'quiero', 'tienes', 'precio', 'cuanto', 'cuesta', 'busco', 'necesito', 'para', 'celular', 'telefono'}
    # V2.2 FIX: Permitir palabras de 2 letras (ej: XR, 11, 12, S9)
    keywords = [w.lower() for w in search_message.split() if len(w) >= 2 and w.lower() not in stop_words]
    
    if keywords:
        # 1. INTENTO ESTRICTO (AND)
        # Construir condiciones: (Nombre LIKE %k1% OR Marca LIKE %k1% OR Modelo LIKE %k1% OR Categoria LIKE %k1%) AND (...)
        and_conditions = []
        for k in keywords:
            term_condition = or_(
                Product.nombre.ilike(f"%{k}%"),
                Product.marca.ilike(f"%{k}%"),
                Product.modelo.ilike(f"%{k}%"),
                Product.sku.ilike(f"%{k}%"),
                Product.categoria.ilike(f"%{k}%") # V2.5: Buscar también en categoría (ej: "Accesorios")
            )
            and_conditions.append(term_condition)
            
        relevant_products = db.query(Product).options(
            joinedload(Product.stock_items).joinedload(Stock.location)
        ).filter(
            Product.activo == True,
            *and_conditions
        ).limit(10).all()
        
        # 2. INTENTO RELAJADO (OR) - Relleno si hay pocos resultados
        if len(relevant_products) < 5:
            existing_ids = [p.id for p in relevant_products]
            
            # Aplanar condiciones para un OR gigante
            or_conditions = []
            for k in keywords:
                or_conditions.append(Product.nombre.ilike(f"%{k}%"))
                or_conditions.append(Product.modelo.ilike(f"%{k}%"))
                or_conditions.append(Product.categoria.ilike(f"%{k}%"))
            
            more_products = db.query(Product).options(
                joinedload(Product.stock_items).joinedload(Stock.location)
            ).filter(
                Product.activo == True,
                Product.id.notin_(existing_ids),
                or_(*or_conditions)
            ).limit(10 - len(relevant_products)).all()
            
            relevant_products.extend(more_products)
            
    # B. Rellenar con Top Stock (lo más vendido/disponible) si aún faltan
    if len(relevant_products) < 10:
        # Optimización: Cargar relaciones para evitar N+1
        top_products = db.query(Product).options(
            joinedload(Product.stock_items).joinedload(Stock.location)
        ).filter(Product.activo == True).limit(20).all()
        # Ordenar por stock total (en Python porque es propiedad computada o relación)
        # Nota: Para eficiencia real, esto debería ser una query SQL con join, pero por ahora:
        top_products.sort(key=lambda p: sum(s.cantidad_disponible for s in p.stock_items), reverse=True)
        
        for p in top_products:
            if p not in relevant_products and len(relevant_products) < 15:
                relevant_products.append(p)

    # 4.5 Pre-cargar Bancos para cálculos de cuotas en inventario
    banks = db.query(Bank).filter(Bank.active == True).all()
    default_bank_rate = 0.05 # Fallback 5%
    default_months = 12
    
    # Intentar encontrar una tasa real para el ejemplo
    if banks:
        for b in banks:
            for opt in b.financing_options:
                if opt.active and opt.months == 12:
                    default_bank_rate = float(opt.rate)
                    break

    inventory_text = "INVENTARIO DISPONIBLE (Ubicación: ID):\n"
    has_inventory = False
    
    for p in relevant_products:
        # V2.4 SAFETY: Ignorar productos sin precio o precio cero
        if not p.precio or p.precio <= 0:
            continue

        stock_details = []
        total_stock_real = 0
        
        # Ordenar stock items para mostrar primero los que tienen más stock
        # (Esto se hace en memoria porque ya se cargaron con joinedload)
        sorted_stock = sorted(p.stock_items, key=lambda s: (s.cantidad_disponible - s.cantidad_reservada), reverse=True)
        
        for s in sorted_stock:
            # CÁLCULO DE STOCK REAL: Disponible - Reservado
            # V2.5 FIX: Asegurar que no sea negativo
            stock_libre = max(0, (s.cantidad_disponible or 0) - (s.cantidad_reservada or 0))
            
            if stock_libre > 0:
                # Intentar obtener nombre de ubicación de forma segura
                # V2.2 FIX: Verificar que la ubicación esté activa
                if s.location and s.location.activo:
                    loc_name = s.location.nombre
                    stock_details.append(f"{stock_libre} en {loc_name} (ID:{s.location_id})")
                    total_stock_real += stock_libre
        
        if total_stock_real > 0:
            has_inventory = True
            details_str = ", ".join(stock_details)
            color_info = f" Color: {p.color}" if p.color else ""
            # Formato de precio mejorado
            precio_fmt = f"{p.precio:,.2f}"
            
            # V2.4: Pre-cálculo de cuota para ayudar al bot
            # Fórmula: (Precio * (1 + Tasa)) / Meses
            try:
                precio_float = float(p.precio)
                cuota_aprox = (precio_float * (1 + default_bank_rate)) / default_months
                cuota_fmt = f"{cuota_aprox:,.2f}"
                financing_hint = f" | Cuota aprox 12m: {p.moneda} {cuota_fmt}"
            except:
                financing_hint = ""
            
            # V2.5: Alerta de Stock Bajo
            low_stock_alert = " [⚠️ POCAS UNIDADES]" if total_stock_real < 3 else ""

            inventory_text += f"- {p.nombre} ({p.capacidad or ''}){color_info}: {p.moneda} {precio_fmt}{financing_hint} | Disp: {total_stock_real}{low_stock_alert} [{details_str}]\n"
            
    if not has_inventory:
        inventory_text += "NO SE ENCONTRARON PRODUCTOS SIMILARES EN EL INVENTARIO.\n"
            
    # 5. Obtener FAQs Relevantes
    # Estrategia Híbrida: Palabras clave + Recientes + Populares
    relevant_faqs = []
    
    # A. Búsqueda por palabras clave (simple)
    keywords = [w.lower() for w in request.message_content.split() if len(w) > 3]
    
    if keywords:
        # Construir query OR para palabras clave
        conditions = [FAQEntry.pregunta_clave.ilike(f"%{k}%") for k in keywords]
        if conditions:
            relevant_faqs = db.query(FAQEntry).filter(
                FAQEntry.activa == True,
                or_(*conditions)
            ).limit(5).all()
            
    # B. Si no hay suficientes, rellenar con las más recientes (para que lo nuevo aparezca)
    if len(relevant_faqs) < 5:
        recent_faqs = db.query(FAQEntry).filter(FAQEntry.activa == True).order_by(FAQEntry.created_at.desc()).limit(5).all()
        for f in recent_faqs:
            if f not in relevant_faqs and len(relevant_faqs) < 5:
                relevant_faqs.append(f)
                
    # C. Si aún faltan, rellenar con populares
    if len(relevant_faqs) < 5:
        popular_faqs = db.query(FAQEntry).filter(FAQEntry.activa == True).order_by(FAQEntry.veces_usada.desc()).limit(5).all()
        for f in popular_faqs:
            if f not in relevant_faqs and len(relevant_faqs) < 5:
                relevant_faqs.append(f)

    faq_text = "PREGUNTAS FRECUENTES:\n"
    for f in relevant_faqs:
        faq_text += f"P: {f.pregunta_clave}\nR: {f.respuesta}\n"

    # 6. Información de Financiamiento
    banks = db.query(Bank).filter(Bank.active == True).all()
    financing_text = "OPCIONES DE FINANCIAMIENTO Y TARJETAS:\n"
    
    if not banks:
        financing_text += "No hay opciones de financiamiento activas actualmente.\n"
    else:
        for bank in banks:
            rate_pct = float(bank.normal_card_rate) * 100
            financing_text += f"- {bank.name}: Tasa Tarjeta Normal {rate_pct:.2f}%\n"
            
            active_options = [opt for opt in bank.financing_options if opt.active]
            if active_options:
                financing_text += "  Extrafinanciamiento:\n"
                for opt in active_options:
                    opt_rate_pct = float(opt.rate) * 100
                    financing_text += f"  * {opt.months} Meses: {opt_rate_pct:.2f}% recargo total\n"
    
    financing_text += "\nNOTA PARA EL BOT: Para calcular cuota mensual: (Precio + (Precio * %Recargo)) / Meses.\n"
    financing_text += "EJEMPLO: Precio 10,000, Recargo 5% (0.05), 12 Meses -> (10000 + 500) / 12 = 875 mensual.\n"
    financing_text += "Si el cliente paga prima, restar prima antes de calcular recargo.\n"
    financing_text += "IMPORTANTE: NO ofrecemos crédito directo, fiado, ni pagos parciales sin tarjeta. Todo es de contado o con tarjeta de crédito.\n"

    # --- PROTOCOLO DE RETOMAS (TRADE-IN) ---
    # Obtener políticas dinámicas de la base de datos
    trade_in_policies = db.query(TradeInPolicy).filter(TradeInPolicy.is_active == True).all()
    
    financing_text += "\nPROTOCOLO DE RETOMAS (TRADE-IN):\n"
    financing_text += "POLÍTICA DE MARCAS Y MODELOS:\n"
    
    if not trade_in_policies:
        # Fallback por defecto si no hay reglas en DB
        financing_text += "- ACEPTAMOS ÚNICAMENTE: Apple (iPhone) y Samsung.\n"
        financing_text += "- RECHAZAMOS AUTOMÁTICAMENTE: Huawei, Xiaomi, Motorola, LG, Google Pixel, Tablets, Relojes, Laptops, Consolas, etc.\n"
        financing_text += "- MODELOS RECHAZADOS: iPhone 8 o inferior, Samsung S10 o inferior, Serie A antigua.\n"
    else:
        accepted_brands = []
        rejected_patterns = []
        
        for policy in trade_in_policies:
            if policy.action == 'reject':
                reason_str = f" ({policy.reason})" if policy.reason else ""
                rejected_patterns.append(f"{policy.pattern}{reason_str}")
            elif policy.action == 'accept_with_conditions':
                accepted_brands.append(policy.pattern)
                
        if accepted_brands:
            financing_text += f"- ACEPTAMOS PREFERENTEMENTE: {', '.join(accepted_brands)}.\n"
        if rejected_patterns:
            financing_text += "- RECHAZAMOS AUTOMÁTICAMENTE LOS SIGUIENTES MODELOS/MARCAS:\n"
            for p in rejected_patterns:
                financing_text += f"  * {p}\n"
    
    financing_text += "\nINSTRUCCIONES DE INTERACCIÓN:\n"
    financing_text += "1. Consulta la lista de RECHAZADOS arriba. Si el cliente ofrece algo que coincida con un patrón rechazado, responde amablemente que NO lo aceptamos y explica la razón si existe.\n"
    financing_text += "2. Si la marca/modelo NO está rechazado explícitamente y parece ser de gama alta/reciente, ENTONCES procede a pedir los datos obligatorios: Modelo exacto, Color, Capacidad (GB), Estado (pantalla, batería, detalles estéticos), ¿Está liberado?\n"
    financing_text += "3. Una vez tengas los datos, di: 'Gracias, consultaré con el técnico el valor de retoma. Un momento por favor.'\n"
    financing_text += "4. Si tienes un número de encargado configurado, menciona que le enviarás los datos.\n"
    financing_text += "5. CÁLCULO DE DIFERENCIA: Precio Nuevo - Valor Retoma = Diferencia a Pagar.\n"
    financing_text += "6. Si paga la diferencia con TARJETA/FINANCIAMIENTO: El recargo se aplica SOLO a la Diferencia a Pagar.\n"
    financing_text += "   Fórmula: (Diferencia + (Diferencia * %Recargo)) / Meses.\n"

    # 7. Historial Reciente (Últimos 10 mensajes)
    recent_logs = db.query(InteractionLog).filter(
        InteractionLog.customer_id == customer.id
    ).order_by(InteractionLog.created_at.desc()).limit(10).all()
    
    # V2.4: Agregar timestamps relativos al historial
    context_history = []
    reference_now = _utcnow()
    
    for log in reversed(recent_logs):
        # Calcular diferencia de tiempo amigable
        try:
            # Asumiendo que log.created_at es naive UTC o timezone aware, normalizar
            log_time = log.created_at
            if log_time is None:
                raise ValueError("log_time missing")
            if log_time.tzinfo is None:
                normalized_log_time = log_time.replace(tzinfo=UTC)
            else:
                normalized_log_time = log_time.astimezone(UTC)
            diff = reference_now - normalized_log_time
                
            minutes = int(diff.total_seconds() / 60)
            hours = int(minutes / 60)
            days = int(hours / 24)
            
            if days > 0:
                time_str = f"[Hace {days} días]"
            elif hours > 0:
                time_str = f"[Hace {hours} horas]"
            elif minutes > 0:
                time_str = f"[Hace {minutes} min]"
            else:
                time_str = "[Ahora]"
        except:
            time_str = ""
            
        # V2.5 SAFETY: Truncar mensajes muy largos para ahorrar tokens
        content_safe = log.content[:500] + "..." if len(log.content) > 500 else log.content
        
        context_history.append({
            "role": log.role, 
            "content": f"{time_str} {content_safe}"
        })

    # Combinar prompt del sistema con instrucción troll si aplica
    final_system_prompt = ai_config.system_prompt
    
    # --- INYECCIÓN DINÁMICA DE REGLAS V2.2 (Sobrescribe prompt estático si es necesario) ---
    # Esto asegura que si cambias la config pero no regeneras el prompt, el bot igual se entere.
    dynamic_instructions = []
    
    # Manejo seguro de valores nulos/Decimal para configuración de negociación
    neg_style = (ai_config.negotiation_style or '').strip()
    try:
        max_discount = float(ai_config.max_discount_rate or 0.0)
    except Exception:
        max_discount = 0.0

    if neg_style == 'flexible' and max_discount > 0:
        discount_pct = int(max_discount * 100)
        dynamic_instructions.append(f"ACTUALIZACIÓN DE NEGOCIACIÓN: Tienes autorizado ofrecer hasta {discount_pct}% de descuento si es CRÍTICO para cerrar la venta.")
        
    if ai_config.fallback_human_trigger:
        dynamic_instructions.append(f"ALERTA DE TRANSFERENCIA: Si detectas la intención '{ai_config.fallback_human_trigger}', transfiere a humano inmediatamente.")
        
    # V2.3: Inyección de Contexto Temporal y Monetario
    now = datetime.now()
    current_time_str = now.strftime("%A %d de %B, %I:%M %p")
    
    dynamic_instructions.append(f"CONTEXTO TEMPORAL: La fecha y hora actual es {current_time_str}. Usa esto para saludar adecuadamente (Buenos días/tardes/noches).")
    dynamic_instructions.append(f"TASA DE CAMBIO: 1 USD = {exchange_rate} HNL (Lempiras). Si el cliente pide precios en Lempiras, haz la conversión usando esta tasa.")

    if dynamic_instructions:
        final_system_prompt += "\n\n[INSTRUCCIONES DINÁMICAS DEL SISTEMA]:\n" + "\n".join(dynamic_instructions)

    if memory_hint:
        final_system_prompt += f"\n\n[MEMORIA DEL CLIENTE]:\n{memory_hint}"

    if semantic_memories:
        final_system_prompt += "\n\n[RECUERDOS RELEVANTES RECUPERADOS]:\n" + "\n".join(f"- {snippet}" for snippet in semantic_memories)

    final_system_prompt += "\n\n" + BOT_PHOTO_DETECTION_INSTRUCTIONS
    
    # Inyectar reglas de contexto personalizadas si existen
    if ai_config.context_rules:
        final_system_prompt += f"\n\nREGLAS DE CONTEXTO ADICIONALES:\n{ai_config.context_rules}"
    
    if troll_instruction:
        final_system_prompt += troll_instruction

    return AIContextResponse(
        system_prompt=final_system_prompt,
        bot_config={
            "model": ai_config.model_name,
            "temperature": ai_config.temperature,
            "tone": ai_config.voice_tone,
            "context_rules": ai_config.context_rules,
            "admin_phone": ai_config.admin_notification_phone or "el encargado",
            # V2.2 Fields
            "sales_goal": ai_config.sales_goal,
            "negotiation_style": ai_config.negotiation_style,
            "max_discount_rate": float(ai_config.max_discount_rate or 0),
            "fallback_trigger": ai_config.fallback_human_trigger,
            # V2.3 Fields
            "exchange_rate": exchange_rate,
            "server_time": current_time_str
        },
        customer_info={
            "name": customer.name,
            "is_troll": customer.is_troll,
            "reputation": customer.reputation_score,
            "conversation_summary": customer.conversation_summary,
            "ai_memory": memory,
            "last_referenced_product_id": customer.last_referenced_product_id,
            "last_referenced_product_name": customer.last_referenced_product_name,
            "last_referenced_color": customer.last_referenced_color,
            "last_referenced_variant": customer.last_referenced_variant,
            "semantic_memories": semantic_memories,
        },
        relevant_inventory=inventory_text,
        relevant_faqs=faq_text,
        financing_info=financing_text,
        previous_context=context_history
    )


@router.post("/reply", response_model=AIReplyResponse)
def generate_ai_reply(
    request: AIReplyRequest,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(_require_ai_integration_auth),
):
    """Genera una respuesta completa usando el cliente oficial de OpenAI."""
    if not prod_settings.ENABLE_AI_FEATURES:
        raise HTTPException(status_code=503, detail="Las funcionalidades de IA estan deshabilitadas")
    if not prod_settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY no esta configurada")

    context = get_ai_context(request, db)
    messages = _compose_ai_messages(context, request.message_content, request.conversation_override)

    try:
        completion = openai_service.create_chat_completion(
            messages=messages,
            model=context.bot_config.get("model"),
            temperature=context.bot_config.get("temperature"),
        )
    except RuntimeError:
        _increment_metric("fallback_replies")
        fallback_reply = _build_local_fallback_reply(context, request.message_content)

        normalized_phone = _normalize_phone(request.customer_phone)
        profile = db.query(SalesProfile).filter(SalesProfile.slug == request.sales_profile_slug).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Sales Profile not found")

        customer = db.query(Customer).filter(Customer.phone_number == normalized_phone).first()
        if not customer:
            customer = db.query(Customer).filter(Customer.phone_number == request.customer_phone).first()
        if customer:
            user_log = InteractionLogCreate(
                sales_profile_slug=request.sales_profile_slug,
                customer_phone=customer.phone_number,
                role="user",
                content=request.message_content,
                tokens_used=0,
            )
            bot_log = InteractionLogCreate(
                sales_profile_slug=request.sales_profile_slug,
                customer_phone=customer.phone_number,
                role="assistant",
                content=fallback_reply,
                tokens_used=0,
            )
            log_interaction(user_log, db)
            log_interaction(bot_log, db)

        return AIReplyResponse(
            reply=fallback_reply,
            tokens_used=0,
            model="fallback-local",
            context=context,
        )

    reply_text = (completion.get("reply") or "").strip()
    _increment_metric("openai_replies")
    usage = completion.get("usage") or {}
    tokens_used = int(usage.get("total_tokens") or 0)
    model_name = completion.get("model") or context.bot_config.get("model") or prod_settings.OPENAI_MODEL

    normalized_phone = _normalize_phone(request.customer_phone)
    profile = db.query(SalesProfile).filter(SalesProfile.slug == request.sales_profile_slug).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Sales Profile not found")

    customer = db.query(Customer).filter(Customer.phone_number == normalized_phone).first()
    if not customer:
        customer = db.query(Customer).filter(Customer.phone_number == request.customer_phone).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer_phone_value = customer.phone_number
    matched_products = _find_candidate_products(db, request.message_content, customer, limit=3)

    user_log = InteractionLogCreate(
        sales_profile_slug=request.sales_profile_slug,
        customer_phone=customer_phone_value,
        role="user",
        content=request.message_content,
        tokens_used=0,
    )
    bot_log = InteractionLogCreate(
        sales_profile_slug=request.sales_profile_slug,
        customer_phone=customer_phone_value,
        role="assistant",
        content=reply_text,
        tokens_used=tokens_used,
    )

    log_interaction(user_log, db)
    log_interaction(bot_log, db)

    color_requested, size_requested = extract_photo_request_context(request.message_content)
    _update_customer_memory(
        db,
        customer,
        request.message_content,
        matched_products=matched_products,
        bot_reply=reply_text,
        color_requested=color_requested,
        size_requested=size_requested,
    )
    db.commit()

    return AIReplyResponse(
        reply=reply_text,
        tokens_used=tokens_used,
        model=model_name,
        context=context,
    )

@router.post("/log")
def log_interaction(
    log_data: InteractionLogCreate,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(_require_ai_integration_auth),
):
    """Guarda un mensaje en el historial"""
    profile = db.query(SalesProfile).filter(SalesProfile.slug == log_data.sales_profile_slug).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    customer = db.query(Customer).filter(Customer.phone_number == log_data.customer_phone).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    new_log = InteractionLog(
        customer_id=customer.id,
        sales_profile_id=profile.id,
        role=log_data.role,
        content=log_data.content,
        tokens_used=log_data.tokens_used
    )
    db.add(new_log)
    
    # Actualizar contadores del cliente
    now = _utcnow()
    
    # V2.5: Resetear contador diario si es un nuevo día
    if customer.last_interaction_at:
        last_date = customer.last_interaction_at.date()
        current_date = now.date()
        if current_date > last_date:
            customer.daily_message_count = 0
            
    customer.last_interaction_at = now
    customer.daily_message_count += 1
    
    db.commit()
    return {"status": "logged"}

@router.post("/training/submit")
def submit_training_example(
    submission: TrainingSubmission,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(_require_ai_integration_auth),
):
    """n8n envía una pregunta que no supo responder bien"""
    profile = db.query(SalesProfile).filter(SalesProfile.slug == submission.sales_profile_slug).first()
    
    queue_item = TrainingQueue(
        sales_profile_id=profile.id if profile else None,
        customer_question=submission.customer_question,
        ai_proposed_answer=submission.ai_proposed_answer,
        status="pending"
    )
    db.add(queue_item)
    db.commit()
    return {"status": "submitted_for_review"}

@router.post("/flag-troll")
def flag_troll(
    phone_number: str = Body(..., embed=True),
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(_require_ai_integration_auth),
):
    """Marca un cliente como troll manualmente o por IA"""
    customer = db.query(Customer).filter(Customer.phone_number == phone_number).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    customer.is_troll = True
    customer.reputation_score = 0
    customer.notes = (customer.notes or "") + f"\n[AUTO-FLAG] Marcado como troll: {reason}"
    
    db.commit()
    return {"status": "flagged", "customer": customer.phone_number}

# --- Training & Insights Endpoints ---

@router.get(
    "/training-queue",
    response_model=PaginatedResponse[TrainingQueueItemResponse],
)
def list_training_queue(
    status: str = Query("pending", description="Filtrar por estado"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=10, le=200, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """Lista preguntas pendientes de revisión con paginación."""

    query = (
        db.query(TrainingQueue)
        .options(joinedload(TrainingQueue.sales_profile))
        .filter(TrainingQueue.status == status)
    )

    total = query.count()
    offset = (page - 1) * per_page
    sort_column = getattr(TrainingQueue, "created_at", TrainingQueue.id)
    items = (
        query.order_by(sort_column.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    records = [
        TrainingQueueItemResponse(
            id=item.id,
            sales_profile_id=item.sales_profile_id,
            customer_question=item.customer_question,
            ai_proposed_answer=item.ai_proposed_answer,
            admin_correction=item.admin_correction,
            status=item.status,
            created_at=getattr(item, "created_at", None) or datetime.now(UTC),
            sales_profile_name=item.sales_profile.name if item.sales_profile else None,
        )
        for item in items
    ]

    pages = max(0, (total + per_page - 1) // per_page)
    return PaginatedResponse(
        items=records,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )

@router.post("/training-queue/{item_id}/resolve")
def resolve_training_item(
    item_id: int,
    action: str = Body(..., embed=True),
    correction: str = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """Resuelve un item de entrenamiento: aprobar, rechazar o convertir a FAQ"""
    item = db.query(TrainingQueue).filter(TrainingQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    if action == "convert_to_faq":
        if not correction:
            raise HTTPException(status_code=400, detail="Correction required for FAQ")
        
        # Crear FAQ automáticamente
        # Verificar si ya existe una FAQ similar para evitar duplicados
        existing_faq = db.query(FAQEntry).filter(FAQEntry.pregunta_clave == item.customer_question[:255]).first()
        if existing_faq:
            # Actualizar la existente en lugar de crear duplicado
            existing_faq.respuesta = correction
            existing_faq.veces_usada += 1
        else:
            new_faq = FAQEntry(
                pregunta_clave=item.customer_question[:255],
                respuesta=correction,
                categoria="general",
                activa=True
            )
            db.add(new_faq)
            
        item.status = "converted_to_faq"
        item.admin_correction = correction
        
    elif action == "reject":
        item.status = "rejected"
    elif action == "approve":
        item.status = "approved"
        
    db.commit()
    return {"status": "resolved"}


@router.patch("/training-queue/{item_id}", response_model=TrainingQueueItemResponse)
def update_training_queue_item(
    item_id: int,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view")),
):
    """Actualiza campos de un item de training queue en modo API."""
    item = (
        db.query(TrainingQueue)
        .options(joinedload(TrainingQueue.sales_profile))
        .filter(TrainingQueue.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    allowed_fields = {
        "customer_question",
        "ai_proposed_answer",
        "admin_correction",
        "status",
        "sales_profile_id",
    }
    unknown_fields = [key for key in updates.keys() if key not in allowed_fields]
    if unknown_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Campos no permitidos para update: {', '.join(unknown_fields)}",
        )

    if "sales_profile_id" in updates and updates["sales_profile_id"] is not None:
        profile_exists = (
            db.query(SalesProfile)
            .filter(SalesProfile.id == updates["sales_profile_id"])
            .first()
        )
        if not profile_exists:
            raise HTTPException(status_code=404, detail="Sales profile not found")

    if "status" in updates:
        valid_statuses = {"pending", "approved", "rejected", "converted_to_faq"}
        requested_status = str(updates["status"])
        if requested_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Status inválido: {requested_status}. Válidos: {', '.join(sorted(valid_statuses))}",
            )

        if requested_status == "converted_to_faq":
            correction = updates.get("admin_correction") or item.admin_correction
            if not correction:
                raise HTTPException(
                    status_code=400,
                    detail="admin_correction es requerido cuando status=converted_to_faq",
                )
            existing_faq = (
                db.query(FAQEntry)
                .filter(FAQEntry.pregunta_clave == item.customer_question[:255])
                .first()
            )
            if existing_faq:
                existing_faq.respuesta = correction
                existing_faq.veces_usada += 1
            else:
                db.add(
                    FAQEntry(
                        pregunta_clave=item.customer_question[:255],
                        respuesta=correction,
                        categoria="general",
                        activa=True,
                    )
                )

    for field, value in updates.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)

    return TrainingQueueItemResponse(
        id=item.id,
        sales_profile_id=item.sales_profile_id,
        customer_question=item.customer_question,
        ai_proposed_answer=item.ai_proposed_answer,
        admin_correction=item.admin_correction,
        status=item.status,
        created_at=getattr(item, "created_at", None) or datetime.now(UTC),
        sales_profile_name=item.sales_profile.name if item.sales_profile else None,
    )

@router.get(
    "/customers",
    response_model=PaginatedResponse[AICustomerResponse],
)
def list_customers_ai(
    search: Optional[str] = Query(None, description="Texto a buscar por nombre o teléfono"),
    is_troll: Optional[bool] = Query(None, description="Filtrar por clientes marcados como troll"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=10, le=200, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """Lista clientes con datos de inteligencia."""

    query = db.query(Customer)

    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Customer.phone_number.ilike(like_term),
                Customer.name.ilike(like_term),
            )
        )

    if is_troll is not None:
        query = query.filter(Customer.is_troll == is_troll)

    total = query.count()
    offset = (page - 1) * per_page
    customers = (
        query.order_by(Customer.last_interaction_at.desc().nullslast(), Customer.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    records = [
        AICustomerResponse(
            id=customer.id,
            phone_number=customer.phone_number,
            name=customer.name,
            email=customer.email,
            notes=customer.notes,
            is_troll=customer.is_troll,
            is_blocked=customer.is_blocked,
            reputation_score=customer.reputation_score,
            daily_message_count=customer.daily_message_count,
            last_interaction_at=customer.last_interaction_at,
            conversation_summary=customer.conversation_summary,
            ai_memory_json=customer.ai_memory_json,
            last_referenced_product_id=customer.last_referenced_product_id,
            last_referenced_product_name=customer.last_referenced_product_name,
            last_referenced_color=customer.last_referenced_color,
            last_referenced_variant=customer.last_referenced_variant,
            memory_updated_at=customer.memory_updated_at,
            created_at=customer.created_at,
        )
        for customer in customers
    ]

    pages = max(0, (total + per_page - 1) // per_page)
    return PaginatedResponse(
        items=records,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )

@router.patch("/customers/{customer_id}")
def update_customer_ai(
    customer_id: int,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """Actualiza estado de cliente (bloqueo, troll, notas)"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    if "is_troll" in updates:
        customer.is_troll = updates["is_troll"]
    if "is_blocked" in updates:
        customer.is_blocked = updates["is_blocked"]
    if "notes" in updates:
        customer.notes = updates["notes"]
    if "name" in updates:
        customer.name = updates["name"]
    if "email" in updates:
        customer.email = updates["email"]
        
    db.commit()
    db.refresh(customer)
    
    return {
        "id": customer.id,
        "phone_number": customer.phone_number,
        "name": customer.name,
        "email": customer.email,
        "notes": customer.notes,
        "is_troll": customer.is_troll,
        "is_blocked": customer.is_blocked,
        "reputation_score": customer.reputation_score,
        "daily_message_count": customer.daily_message_count,
        "last_interaction_at": customer.last_interaction_at,
        "created_at": customer.created_at
    }


# --- Trade-In Policies Endpoints ---

@router.get("/trade-in-policies", response_model=List[TradeInPolicyResponse])
def list_trade_in_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:view"))
):
    """Lista todas las políticas de retoma"""
    return db.query(TradeInPolicy).order_by(TradeInPolicy.created_at.desc()).all()

@router.post("/trade-in-policies", response_model=TradeInPolicyResponse)
def create_trade_in_policy(
    policy: TradeInPolicyCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:edit"))
):
    """Crea una nueva política de retoma"""
    new_policy = TradeInPolicy(**policy.dict())
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)
    return new_policy

@router.delete("/trade-in-policies/{policy_id}")
def delete_trade_in_policy(
    policy_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:edit"))
):
    """Elimina una política de retoma"""
    policy = db.query(TradeInPolicy).filter(TradeInPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    db.delete(policy)
    db.commit()
    return {"status": "deleted"}

@router.post("/link-order")
def link_order_to_interaction(
    request: LinkOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:create"))
):
    """Vincula la última interacción de un cliente con una orden creada (Atribución de Venta)"""
    customer = db.query(Customer).filter(Customer.phone_number == request.customer_phone).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    # Buscar la última interacción del cliente
    last_interaction = db.query(InteractionLog).filter(
        InteractionLog.customer_id == customer.id
    ).order_by(InteractionLog.created_at.desc()).first()
    
    if last_interaction:
        last_interaction.converted_order_id = request.order_id
        db.commit()
        return {"status": "linked", "interaction_id": last_interaction.id}
        
    return {"status": "no_interaction_found"}


def _resolve_product_for_ai_item(
    db: Session,
    *,
    source_location_id: int,
    product_id: Optional[int],
    product_query: Optional[str],
) -> Product:
    if product_id is not None:
        product = (
            db.query(Product)
            .filter(Product.id == product_id, Product.activo == True)
            .first()
        )
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto no encontrado: id={product_id}")
        return product

    normalized_query = (product_query or "").strip()
    if not normalized_query:
        raise HTTPException(status_code=400, detail="Cada item requiere product_id o product_query")

    exact_match = (
        db.query(Product)
        .join(Stock, Stock.product_id == Product.id)
        .filter(
            Product.activo == True,
            Stock.location_id == source_location_id,
            (Stock.cantidad_disponible - Stock.cantidad_reservada) > 0,
            Product.nombre.ilike(normalized_query),
        )
        .first()
    )
    if exact_match:
        return exact_match

    partial_match = (
        db.query(Product)
        .join(Stock, Stock.product_id == Product.id)
        .filter(
            Product.activo == True,
            Stock.location_id == source_location_id,
            (Stock.cantidad_disponible - Stock.cantidad_reservada) > 0,
            or_(
                Product.nombre.ilike(f"%{normalized_query}%"),
                Product.marca.ilike(f"%{normalized_query}%"),
                Product.modelo.ilike(f"%{normalized_query}%"),
                Product.sku.ilike(f"%{normalized_query}%"),
            ),
        )
        .order_by(Product.nombre.asc())
        .first()
    )
    if not partial_match:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró producto para '{normalized_query}' con stock en la ubicación {source_location_id}",
        )
    return partial_match


def _create_order_from_ai_payload(
    request: AICreateOrderRequest,
    db: Session,
    auth_context: Optional[User],
) -> AICreateOrderResponse:
    if not request.items:
        raise HTTPException(status_code=400, detail="Debe incluir al menos un item")

    if request.source_location_id <= 0:
        raise HTTPException(status_code=400, detail="source_location_id debe ser mayor a 0")

    resolved_items: List[Dict[str, Any]] = []
    for index, item in enumerate(request.items):
        if item.cantidad <= 0:
            raise HTTPException(status_code=400, detail=f"Item {index + 1}: cantidad debe ser mayor a 0")

        resolved_product = _resolve_product_for_ai_item(
            db,
            source_location_id=request.source_location_id,
            product_id=item.product_id,
            product_query=item.product_query,
        )

        item_payload: Dict[str, Any] = {
            "product_id": int(resolved_product.id),
            "cantidad": int(item.cantidad),
            "es_regalo_promocion": False,
        }
        if item.precio_unitario is not None:
            item_payload["precio_unitario"] = item.precio_unitario
        if item.imeis:
            item_payload["imeis"] = item.imeis

        resolved_items.append(item_payload)

    order_payload = {
        "sales_profile_slug": request.sales_profile_slug,
        "source_location_id": request.source_location_id,
        "customer_name": (request.customer_name or "Cliente IA").strip() or "Cliente IA",
        "customer_phone": request.customer_phone,
        "canal": request.canal,
        "metodo_pago": request.metodo_pago,
        "items": resolved_items,
        "notes": request.notes,
    }

    order_create = OrderCreate.model_validate(order_payload)
    service = OrderService(db)
    created_order = service.create_order(order_create, current_user=auth_context)

    if not request.auto_link_interaction:
        linked_rows = (
            db.query(InteractionLog)
            .filter(InteractionLog.converted_order_id == created_order.id)
            .all()
        )
        for row in linked_rows:
            row.converted_order_id = None
        if linked_rows:
            db.commit()

    linked_interaction = bool(
        db.query(InteractionLog)
        .filter(InteractionLog.converted_order_id == created_order.id)
        .first()
    )

    return AICreateOrderResponse(
        status="created",
        order_id=int(created_order.id),
        linked_interaction=linked_interaction,
    )


@router.post("/create-order", response_model=AICreateOrderResponse)
def create_order_from_ai(
    request: AICreateOrderRequest,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(_require_ai_integration_auth),
):
    return _create_order_from_ai_payload(request, db, auth_context)


@router.post("/handle-message", response_model=AIHandleMessageResponse)
def handle_message_without_n8n(
    request: AIHandleMessageRequest,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(_require_ai_integration_auth),
):
    started_at = _utcnow()
    _increment_metric("total_messages")

    profile = db.query(SalesProfile).filter(SalesProfile.slug == request.sales_profile_slug).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Sales Profile not found")

    if request.message_id:
        _cleanup_processed_messages(db)
        stored = _mark_message_processed(
            db=db,
            message_id=request.message_id,
            channel=request.channel_hint or _infer_channel_from_sales_profile(profile),
            customer_phone=_normalize_phone(request.customer_phone),
            sales_profile_id=profile.id,
        )
        if not stored:
            _increment_metric("duplicate_messages")
            latest_assistant = db.query(InteractionLog).filter(
                InteractionLog.sales_profile_id == profile.id,
                InteractionLog.role == "assistant",
            ).order_by(InteractionLog.created_at.desc()).first()
            duplicate_reply = latest_assistant.content if latest_assistant and latest_assistant.content else "Mensaje ya procesado recientemente."
            context = get_ai_context(request, db, auth_context)
            return AIHandleMessageResponse(
                reply=duplicate_reply,
                tokens_used=0,
                model="duplicate-guard",
                context=context,
                order=None,
            )

    if detect_photo_request(request.message_content):
        context = get_ai_context(request, db, auth_context)
        normalized_phone = _normalize_phone(request.customer_phone)
        customer = db.query(Customer).filter(Customer.phone_number == normalized_phone).first()
        if not customer:
            customer = db.query(Customer).filter(Customer.phone_number == request.customer_phone).first()
        color_requested, size_requested = extract_photo_request_context(request.message_content)
        candidate_products = _find_candidate_products(db, request.message_content, customer, limit=3)
        selected_product = candidate_products[0] if candidate_products else None
        product_name = str(selected_product.nombre) if selected_product and selected_product.nombre else _find_product_name_hint(db, request.message_content)
        channel = _infer_channel_from_sales_profile(profile)

        create_photo_request_internal(
            db=db,
            data=PhotoRequestCreate(
                customer_id=normalized_phone,
                product_id=int(selected_product.id) if selected_product and selected_product.id else None,
                product_name=product_name,
                color_requested=color_requested,
                size_requested=size_requested,
                additional_notes=f"Auto-created from AI conversation. channel:{channel}",
                customer_name=request.customer_name,
                origin_channel=channel,
            ),
            sales_profile_slug=request.sales_profile_slug,
            channel=channel,
            customer_name=request.customer_name,
        )
        _increment_metric("photo_handoffs")

        if customer:
            _update_customer_memory(
                db,
                customer,
                request.message_content,
                matched_products=candidate_products,
                bot_reply=get_response_for_photo_request(language="es"),
                color_requested=color_requested,
                size_requested=size_requested,
            )
        db.commit()

        bot_response = get_response_for_photo_request(language="es")

        user_log = InteractionLogCreate(
            sales_profile_slug=request.sales_profile_slug,
            customer_phone=normalized_phone,
            role="user",
            content=request.message_content,
            tokens_used=0,
        )
        bot_log = InteractionLogCreate(
            sales_profile_slug=request.sales_profile_slug,
            customer_phone=normalized_phone,
            role="assistant",
            content=bot_response,
            tokens_used=0,
        )
        log_interaction(user_log, db)
        log_interaction(bot_log, db)

        ai_reply = AIReplyResponse(
            reply=bot_response,
            tokens_used=0,
            model="photo-handoff",
            context=context,
        )
    else:
        ai_reply = generate_ai_reply(request, db, auth_context)

    order_result: Optional[AICreateOrderResponse] = None
    intent = request.order_intent
    if intent and intent.auto_create:
        order_request = AICreateOrderRequest(
            sales_profile_slug=request.sales_profile_slug,
            source_location_id=intent.source_location_id,
            customer_phone=request.customer_phone,
            customer_name=request.customer_name,
            canal=intent.canal,
            metodo_pago=intent.metodo_pago,
            items=intent.items,
            notes=intent.notes,
            auto_link_interaction=intent.auto_link_interaction,
        )
        order_result = _create_order_from_ai_payload(order_request, db, auth_context)
        _increment_metric("orders_created")

    elapsed_ms = (_utcnow() - started_at).total_seconds() * 1000.0
    _record_latency_ms(elapsed_ms)

    return AIHandleMessageResponse(
        reply=ai_reply.reply,
        tokens_used=ai_reply.tokens_used,
        model=ai_reply.model,
        context=ai_reply.context,
        order=order_result,
    )


@router.get("/runtime-metrics")
def get_ai_runtime_metrics(
    current_user: User = Depends(check_permission("reports:view")),
):
    latencies = _AI_RUNTIME_METRICS.get("latency_ms") or []
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    p95_latency = round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 2) if latencies else 0.0
    return {
        "total_messages": int(_AI_RUNTIME_METRICS.get("total_messages", 0)),
        "photo_handoffs": int(_AI_RUNTIME_METRICS.get("photo_handoffs", 0)),
        "openai_replies": int(_AI_RUNTIME_METRICS.get("openai_replies", 0)),
        "fallback_replies": int(_AI_RUNTIME_METRICS.get("fallback_replies", 0)),
        "duplicate_messages": int(_AI_RUNTIME_METRICS.get("duplicate_messages", 0)),
        "orders_created": int(_AI_RUNTIME_METRICS.get("orders_created", 0)),
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "samples": len(latencies),
    }
