"""Router de Cierre de Día - Validación de ventas por el administrador.

Flujo:
  1. Admin configura un código de validación en ajustes.
  2. Al final del día, admin abre el panel de cierre de día.
  3. Ve todas las órdenes en estado 'completada' que aún no han sido validadas.
  4. Ingresa el código y aprueba → las órdenes pasan a estado 'validada'.
  5. Se registra en StockHistory la confirmación de la salida del producto.
"""

import hashlib
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import check_permission, get_current_active_user
from app.database import get_db
from app.models import Order, Product, StockHistory, SystemConfig, User
from app.schemas.daily_close import (
    DailyCloseConfigRequest,
    DailyCloseConfigResponse,
    DailyCloseOrderSummary,
    DailyCloseValidateRequest,
    DailyCloseValidateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/daily-close", tags=["Cierre de Día"])

# Clave usada en system_config para guardar el código (hasheado)
_CODE_KEY = "daily_close_validation_code"


def _hash_code(code: str) -> str:
    """Hashea el código de validación con SHA-256."""
    return hashlib.sha256(code.strip().encode()).hexdigest()


def _get_stored_code(db: Session) -> SystemConfig | None:
    result = db.query(SystemConfig).filter(SystemConfig.key == _CODE_KEY).first()
    return result


def _build_order_summary(order: Any) -> DailyCloseOrderSummary:
    order_id = cast(int, getattr(order, "id"))
    customer_name = cast(str, getattr(order, "customer_name"))
    customer_phone = cast(str, getattr(order, "customer_phone"))
    canal = cast(str, getattr(order, "canal"))
    metodo_pago = cast(str, getattr(order, "metodo_pago"))
    total_raw = cast(Decimal, getattr(order, "total"))
    estado = cast(str, getattr(order, "estado"))
    created_at = cast(datetime, getattr(order, "created_at"))
    items = cast(list[Any], getattr(order, "items", []))

    items_parts: list[str] = []
    for item in items:
        product = getattr(item, "product", None)
        product_id = cast(int, getattr(item, "product_id"))
        product_name = cast(str, getattr(product, "nombre")) if product is not None else f"Producto #{product_id}"
        cantidad = cast(int, getattr(item, "cantidad"))
        name = product_name
        items_parts.append(f"{name} x{cantidad}")

    return DailyCloseOrderSummary(
        id=order_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        canal=canal,
        metodo_pago=metodo_pago,
        total=float(total_raw),
        estado=estado,
        created_at=created_at,
        items_count=len(items),
        items_summary=", ".join(items_parts) if items_parts else "Sin items",
    )


# ─────────────────────────── CONFIGURACIÓN ────────────────────────────────────

@router.get(
    "/config",
    response_model=DailyCloseConfigResponse,
    summary="Obtener estado de configuración del código de validación",
    dependencies=[Depends(check_permission("settings:view"))],
)
def get_config(db: Session = Depends(get_db)):
    """Indica si el código de validación ya está configurado."""
    stored = _get_stored_code(db)
    stored_value = cast(str | None, getattr(stored, "value", None))
    if stored is not None and bool(stored_value):
        return DailyCloseConfigResponse(
            configured=True,
            mensaje="Código de validación configurado.",
        )
    return DailyCloseConfigResponse(
        configured=False,
        mensaje="No hay código de validación configurado. Configúrelo en Ajustes.",
    )


@router.post(
    "/config",
    response_model=DailyCloseConfigResponse,
    summary="Configurar o cambiar el código de validación (solo admin)",
    dependencies=[Depends(check_permission("settings:edit"))],
)
def set_config(
    payload: DailyCloseConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Configura o actualiza el código de validación para el cierre de día.
    Solo los administradores (con permiso settings:edit) pueden hacerlo.
    """
    if payload.new_code != payload.confirm_code:
        raise HTTPException(status_code=400, detail="Los códigos no coinciden.")

    stored = _get_stored_code(db)
    stored_value = cast(str | None, getattr(stored, "value", None))

    # Si ya existe un código, el admin debe proveer el anterior
    if stored is not None and bool(stored_value):
        if not payload.current_code:
            raise HTTPException(
                status_code=400,
                detail="Debe ingresar el código actual para poder cambiarlo.",
            )
        if stored_value != _hash_code(payload.current_code):
            raise HTTPException(status_code=403, detail="El código actual es incorrecto.")

    new_hash = _hash_code(payload.new_code)
    username = cast(str, getattr(current_user, "username", "desconocido"))

    if stored is not None:
        setattr(stored, "value", new_hash)
        setattr(stored, "updated_by", username)
    else:
        stored = SystemConfig(
            key=_CODE_KEY,
            value=new_hash,
            description="Código de validación para cierre de día",
            updated_by=username,
        )
        db.add(stored)

    db.commit()
    logger.info("Código de validación de cierre de día actualizado por %s", username)
    return DailyCloseConfigResponse(configured=True, mensaje="Código de validación actualizado exitosamente.")


# ─────────────────────────── CONSULTA PENDIENTES ──────────────────────────────

@router.get(
    "/pending",
    response_model=List[DailyCloseOrderSummary],
    summary="Órdenes completadas pendientes de validación",
    dependencies=[Depends(check_permission("orders:read"))],
)
def get_pending_orders(db: Session = Depends(get_db)):
    """Retorna todas las órdenes en estado 'completada' que todavía
    no han sido validadas (validada_at IS NULL).
    """
    orders = (
        db.query(Order)
        .filter(Order.estado == "completada", Order.validada_at == None)  # noqa: E711
        .order_by(Order.created_at.asc())
        .all()
    )
    return [_build_order_summary(o) for o in orders]


# ─────────────────────────── VALIDAR CIERRE ───────────────────────────────────

@router.post(
    "/validate",
    response_model=DailyCloseValidateResponse,
    summary="Validar ventas del día (solo admin)",
    dependencies=[Depends(check_permission("orders:edit"))],
)
def validate_daily_close(
    payload: DailyCloseValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """El admin ingresa el código de validación y aprueba las órdenes seleccionadas.

    Al validar:
    - Las órdenes pasan a estado 'validada'.
    - Se registra validada_at y validated_by.
    - Se agrega una entrada en StockHistory confirmando la salida del equipo.
    """
    # 1. Verificar que el código esté configurado
    stored = _get_stored_code(db)
    stored_value = cast(str | None, getattr(stored, "value", None))
    if stored is None or not stored_value:
        raise HTTPException(
            status_code=400,
            detail="El código de validación no está configurado. Configúrelo en Ajustes.",
        )

    # 2. Verificar el código ingresado
    if stored_value != _hash_code(payload.validation_code):
        logger.warning(
            "Intento fallido de validación de cierre de día por usuario %s",
            cast(str, getattr(current_user, "username", "desconocido")),
        )
        raise HTTPException(status_code=403, detail="Código de validación incorrecto.")

    validated_ids: List[int] = []
    total_ventas = 0.0
    now = datetime.now(timezone.utc)
    username = cast(str, getattr(current_user, "username", "sistema"))

    try:
        for order_id in payload.order_ids:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                logger.warning("Orden %s no encontrada, se omite en validación", order_id)
                continue

            order_obj = cast(Any, order)
            order_estado = cast(str, getattr(order_obj, "estado"))

            if order_estado != "completada":
                logger.warning(
                    "Orden %s tiene estado '%s', se omite (solo se validan 'completada')",
                    order_id,
                    order_estado,
                )
                continue

            if getattr(order_obj, "validada_at", None) is not None:
                # Ya fue validada anteriormente, no duplicar
                continue

            # Actualizar estado de la orden
            setattr(order_obj, "estado", "validada")
            setattr(order_obj, "validada_at", now)
            setattr(order_obj, "validated_by", username)
            order_total = cast(Decimal, getattr(order_obj, "total"))
            total_ventas += float(order_total)
            validated_ids.append(cast(int, getattr(order_obj, "id")))

            # Registrar en StockHistory la confirmación de salida
            order_items = cast(list[Any], getattr(order_obj, "items", []))
            for item in order_items:
                if cast(bool, getattr(item, "es_regalo_promocion", False)):
                    continue  # No se cobra ni descuenta en inventario

                item_product_id = cast(int, getattr(item, "product_id"))
                product = db.query(Product).filter(Product.id == item_product_id).first()
                if not product:
                    continue

                item_cantidad = cast(int, getattr(item, "cantidad"))
                order_source_location_id = cast(int | None, getattr(order_obj, "source_location_id", None))
                order_ref_id = cast(int, getattr(order_obj, "id"))

                history_entry = StockHistory(
                    product_id=item_product_id,
                    location_id=order_source_location_id,
                    tipo_cambio="VENTA_VALIDADA",
                    cantidad=item_cantidad,
                    stock_anterior=0,   # Ya fue descontado al crear la orden
                    stock_nuevo=0,
                    referencia_id=order_ref_id,
                    referencia_tipo="order_validated",
                    notas=payload.notas or f"Validado en cierre de día por {username}",
                    usuario=username,
                )
                db.add(history_entry)

        db.commit()

        logger.info(
            "Cierre de día: %d órdenes validadas por %s. Total: %.2f",
            len(validated_ids),
            username,
            total_ventas,
        )

        return DailyCloseValidateResponse(
            validated_count=len(validated_ids),
            validated_orders=validated_ids,
            total_ventas=total_ventas,
            mensaje=(
                f"✅ {len(validated_ids)} orden(es) validada(s) exitosamente. "
                f"Total ventas confirmadas: {total_ventas:,.2f}"
            ),
        )

    except Exception as e:
        db.rollback()
        logger.exception("Error al validar cierre de día: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al validar cierre de día: {str(e)}")
