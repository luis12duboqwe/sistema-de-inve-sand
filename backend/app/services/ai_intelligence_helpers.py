from datetime import UTC, datetime
import json
from typing import Any, Dict, List, Optional

from app.schemas import BusinessInsightRecommendation


def safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def isoformat_optional(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.isoformat()


def ensure_aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def parse_ai_business_response(raw_text: str) -> Dict[str, Any]:
    if not raw_text:
        return {}
    try:
        parsed = json.loads(raw_text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(raw_text[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
    return {}


def build_fallback_recommendations(metrics: Dict[str, Any]) -> List[BusinessInsightRecommendation]:
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
                impact=f"Stock restante: {alert.get('stock_available')} uds | Proyección {round(safe_float(alert.get('days_until_stockout')), 1)} días",
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
                impact=f"Ingresos últimos {round(safe_float(top.get('revenue')), 2)} | Margen {round(safe_float(top.get('gross_profit')), 2)}",
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
