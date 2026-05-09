"""Router de Cierre de Día - Validación de ventas por el administrador.

Flujo:
  1. Admin configura un código de validación en ajustes.
  2. Al final del día, admin abre el panel de cierre de día.
  3. Ve todas las órdenes en estado 'completada' que aún no han sido validadas.
  4. Ingresa el código y aprueba → las órdenes pasan a estado 'validada'.
  5. Se registra en StockHistory la confirmación de la salida del producto.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, cast

from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.utils.daily_close_code import (
    DAILY_CLOSE_CODE_KEY,
    get_daily_close_code_hash,
    hash_daily_close_code,
    verify_daily_close_code,
)
from app.utils.location_access import get_accessible_location_ids, require_location_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/daily-close", tags=["Cierre de Día"])

def _get_stored_code(db: Session) -> SystemConfig | None:
    result = db.query(SystemConfig).filter(SystemConfig.key == DAILY_CLOSE_CODE_KEY).first()
    return result


def _build_order_summary(order: Any) -> DailyCloseOrderSummary:
    order_id = cast(int, getattr(order, "id"))
    customer_name = cast(str, getattr(order, "customer_name"))
    customer_phone = cast(str, getattr(order, "customer_phone"))
    canal = cast(str, getattr(order, "canal"))
    metodo_pago = cast(str, getattr(order, "metodo_pago"))
    total_raw = cast(Decimal, getattr(order, "total"))
    estado = cast(str, getattr(order, "estado"))
    source_location_id = cast(int | None, getattr(order, "source_location_id", None))
    source_location = getattr(order, "source_location", None)
    source_location_name = cast(str | None, getattr(source_location, "nombre", None))
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
        source_location_id=source_location_id,
        source_location_name=source_location_name,
        created_at=created_at,
        items_count=len(items),
        items_summary=", ".join(items_parts) if items_parts else "Sin items",
    )


# ─────────────────────────── CONFIGURACIÓN ────────────────────────────────────

@router.get(
    "/config",
    response_model=DailyCloseConfigResponse,
    summary="Obtener estado de configuración del código de validación",
)
def get_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
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
        if not verify_daily_close_code(stored_value, payload.current_code):
            raise HTTPException(status_code=403, detail="El código actual es incorrecto.")

    new_hash = hash_daily_close_code(payload.new_code)
    username = cast(str, getattr(current_user, "username", "desconocido"))

    if stored is not None:
        setattr(stored, "value", new_hash)
        setattr(stored, "updated_by", username)
    else:
        stored = SystemConfig(
            key=DAILY_CLOSE_CODE_KEY,
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
)
def get_pending_orders(
    location_id: int | None = Query(None, gt=0, description="Filtrar por ubicación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:view")),
):
    """Retorna todas las órdenes en estado 'completada' que todavía
    no han sido validadas (validada_at IS NULL).
    """
    query = db.query(Order).filter(
        Order.estado == "completada",
        Order.validada_at == None,  # noqa: E711
    )
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if location_id:
        require_location_access(db, current_user, location_id, "can_view")
        query = query.filter(Order.source_location_id == location_id)
    elif accessible_location_ids is not None:
        query = query.filter(Order.source_location_id.in_(accessible_location_ids))

    orders = query.order_by(Order.created_at.asc()).all()
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
    current_user: User = Depends(check_permission("orders:edit")),
):
    """El admin ingresa el código de validación y aprueba las órdenes seleccionadas.

    Al validar:
    - Las órdenes pasan a estado 'validada'.
    - Se registra validada_at y validated_by.
    - Se agrega una entrada en StockHistory confirmando la salida del equipo.
    """
    # 1. Verificar que el código esté configurado
    stored = _get_stored_code(db)
    stored_value = get_daily_close_code_hash(db)
    if stored is None or not stored_value:
        raise HTTPException(
            status_code=400,
            detail="El código de validación no está configurado. Configúrelo en Ajustes.",
        )

    # 2. Verificar el código ingresado
    if not verify_daily_close_code(stored_value, payload.validation_code):
        logger.warning(
            "Intento fallido de validación de cierre de día por usuario %s",
            cast(str, getattr(current_user, "username", "desconocido")),
        )
        raise HTTPException(status_code=403, detail="Código de validación incorrecto.")

    validated_ids: List[int] = []
    total_ventas = 0.0
    now = datetime.now(timezone.utc)
    username = cast(str, getattr(current_user, "username", "sistema"))

    if payload.location_id:
        require_location_access(db, current_user, payload.location_id, "can_edit")

    try:
        for order_id in payload.order_ids:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                logger.warning("Orden %s no encontrada, se omite en validación", order_id)
                continue

            order_obj = cast(Any, order)
            order_source_location_id = cast(int | None, getattr(order_obj, "source_location_id", None))
            if payload.location_id and order_source_location_id != payload.location_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"La orden #{order_id} no pertenece a la ubicación seleccionada",
                )
            if order_source_location_id:
                require_location_access(db, current_user, order_source_location_id, "can_edit")

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

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error al validar cierre de día: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al validar cierre de día: {str(e)}")
