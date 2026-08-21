"""Router de Cierre de Día - conciliación administrativa de ventas.

Flujo canónico:
  1. Una orden operativa pasa a ``completada`` cuando la venta realmente ocurre.
  2. ``completed_at`` conserva ese momento para reportes y caja.
  3. El cierre de día lista ventas ``completada`` aún no conciliadas.
  4. El responsable ingresa el código y las seleccionadas pasan a ``validada``.
  5. La validación se registra en la bitácora de auditoría; StockHistory queda
     reservado exclusivamente para movimientos reales de inventario.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, List, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import check_permission, get_current_active_user
from app.database import get_db
from app.models import Order, SystemConfig, User
from app.schemas.daily_close import (
    DailyCloseConfigRequest,
    DailyCloseConfigResponse,
    DailyCloseOrderSummary,
    DailyCloseValidateRequest,
    DailyCloseValidateResponse,
)
from app.utils.audit import log_audit_event
from app.utils.daily_close_code import (
    DAILY_CLOSE_CODE_KEY,
    get_daily_close_code_hash,
    hash_daily_close_code,
    verify_daily_close_code,
)
from app.utils.location_access import get_accessible_location_ids, require_location_access
from app.utils.order_integrity import effective_sale_at

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/daily-close", tags=["Cierre de Día"])


def _get_stored_code(db: Session) -> SystemConfig | None:
    return db.query(SystemConfig).filter(SystemConfig.key == DAILY_CLOSE_CODE_KEY).first()


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
    sale_at = effective_sale_at(order) or cast(datetime, getattr(order, "created_at"))
    items = cast(list[Any], getattr(order, "items", []))

    items_parts: list[str] = []
    for item in items:
        product = getattr(item, "product", None)
        product_id = cast(int, getattr(item, "product_id"))
        product_name = cast(str, getattr(product, "nombre")) if product is not None else f"Producto #{product_id}"
        cantidad = cast(int, getattr(item, "cantidad"))
        items_parts.append(f"{product_name} x{cantidad}")

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
        # Se mantiene el nombre del campo por compatibilidad del frontend, pero su
        # semántica para el cierre es la fecha efectiva de la venta.
        created_at=sale_at,
        items_count=len(items),
        items_summary=", ".join(items_parts) if items_parts else "Sin items",
    )


@router.get(
    "/config",
    response_model=DailyCloseConfigResponse,
    summary="Obtener estado de configuración del código de validación",
)
def get_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),  # noqa: ARG001
):
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
    if payload.new_code != payload.confirm_code:
        raise HTTPException(status_code=400, detail="Los códigos no coinciden.")

    stored = _get_stored_code(db)
    stored_value = cast(str | None, getattr(stored, "value", None))

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


@router.get(
    "/pending",
    response_model=List[DailyCloseOrderSummary],
    summary="Ventas completadas pendientes de conciliación",
)
def get_pending_orders(
    location_id: int | None = Query(None, gt=0, description="Filtrar por ubicación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("orders:view")),
):
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

    # completed_at puede ser NULL solo en datos legacy previos a la migración.
    orders = query.order_by(Order.completed_at.asc(), Order.created_at.asc()).all()
    return [_build_order_summary(order) for order in orders]


@router.post(
    "/validate",
    response_model=DailyCloseValidateResponse,
    summary="Conciliar ventas del cierre de día",
    dependencies=[Depends(check_permission("cash_closes:manage"))],
)
def validate_daily_close(
    payload: DailyCloseValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("cash_closes:manage")),
):
    stored = _get_stored_code(db)
    stored_value = get_daily_close_code_hash(db)
    if stored is None or not stored_value:
        raise HTTPException(
            status_code=400,
            detail="El código de validación no está configurado. Configúrelo en Ajustes.",
        )

    if not verify_daily_close_code(stored_value, payload.validation_code):
        logger.warning(
            "Intento fallido de validación de cierre de día por usuario %s",
            cast(str, getattr(current_user, "username", "desconocido")),
        )
        raise HTTPException(status_code=403, detail="Código de validación incorrecto.")

    validated_ids: List[int] = []
    total_ventas = 0.0
    now = datetime.now(UTC)
    username = cast(str, getattr(current_user, "username", "sistema"))

    if payload.location_id:
        require_location_access(db, current_user, payload.location_id, "can_close_cash")

    try:
        # PostgreSQL row locks must be acquired deterministically. Sorting and
        # deduplicating prevents overlapping close requests such as [1, 2] and [2, 1]
        # from taking the same Order locks in opposite order and deadlocking.
        for order_id in sorted(set(payload.order_ids)):
            order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
            if not order:
                logger.warning("Orden %s no encontrada, se omite en validación", order_id)
                continue

            order_source_location_id = cast(int | None, getattr(order, "source_location_id", None))
            if payload.location_id and order_source_location_id != payload.location_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"La orden #{order_id} no pertenece a la ubicación seleccionada",
                )
            if order_source_location_id:
                require_location_access(db, current_user, order_source_location_id, "can_close_cash")

            if order.estado != "completada":
                logger.warning(
                    "Orden %s tiene estado '%s', se omite (solo se concilian ventas completadas)",
                    order_id,
                    order.estado,
                )
                continue

            if order.validada_at is not None:
                continue

            before = {
                "estado": order.estado,
                "completed_at": order.completed_at.isoformat() if order.completed_at else None,
                "validada_at": None,
            }
            if order.completed_at is None:
                # Legacy conservador: no inventamos una hora distinta; mantenemos el
                # mejor dato histórico disponible.
                order.completed_at = order.created_at or now
            order.estado = "validada"
            order.validada_at = now
            order.validated_by = username
            total_ventas += float(order.total)
            validated_ids.append(int(order.id))

            log_audit_event(
                db,
                action="order.daily_close_validate",
                entity_type="order",
                entity_id=order.id,
                location_id=order_source_location_id,
                user=current_user,
                before_data=before,
                after_data={
                    "estado": order.estado,
                    "completed_at": order.completed_at.isoformat() if order.completed_at else None,
                    "validada_at": order.validada_at.isoformat(),
                    "validated_by": username,
                },
                metadata={"notes": payload.notas},
            )

        db.commit()

        logger.info(
            "Cierre de día: %d órdenes conciliadas por %s. Total: %.2f",
            len(validated_ids),
            username,
            total_ventas,
        )

        return DailyCloseValidateResponse(
            validated_count=len(validated_ids),
            validated_orders=validated_ids,
            total_ventas=total_ventas,
            mensaje=(
                f"✅ {len(validated_ids)} venta(s) conciliada(s) exitosamente. "
                f"Total confirmado: {total_ventas:,.2f}"
            ),
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Error al validar cierre de día")
        raise HTTPException(
            status_code=500,
            detail="Error interno al validar el cierre de día. Intente nuevamente o contacte al administrador.",
        ) from exc
