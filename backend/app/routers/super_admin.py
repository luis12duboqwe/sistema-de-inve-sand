from datetime import UTC, datetime, timedelta
import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import AuditLog, IMEIHistory, Location, Order, Product, ProductIMEI, Role, Stock, StockHistory, StockTransfer, User
from app.schemas.order import MetodoPagoEnum, PaymentBreakdownEntry
from app.services.order_service import serialize_payment_breakdown
from app.utils.audit import log_audit_event
from app.utils.stock_manager import StockManager, StockValidationError

router = APIRouter(prefix="/api/super-admin", tags=["super_admin"])


async def get_current_superuser_audited(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if current_user.is_superuser:
        return current_user

    log_audit_event(
        db,
        action="super_admin.access.denied",
        entity_type="access",
        user=current_user,
        metadata={"reason": "Intento de acceso a panel Super Admin"},
    )
    db.commit()
    raise HTTPException(status_code=403, detail="Solo Super Admin puede usar este panel")


class ReasonPayload(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Debe indicar un motivo claro")
        return value


class StockAdjustmentRequest(ReasonPayload):
    product_id: int = Field(..., gt=0)
    location_id: int = Field(..., gt=0)
    cantidad_disponible: int = Field(..., ge=0)
    cantidad_reservada: int = Field(0, ge=0)
    cantidad_defectuosa: int = Field(0, ge=0)

    @model_validator(mode="after")
    def validate_stock_invariants(self) -> "StockAdjustmentRequest":
        if self.cantidad_reservada > self.cantidad_disponible:
            raise ValueError("El stock reservado no puede ser mayor que el disponible")
        return self


class OrderPaymentCorrectionRequest(ReasonPayload):
    metodo_pago: Optional[MetodoPagoEnum] = None
    payment_breakdown: Optional[list[PaymentBreakdownEntry]] = None
    transfer_bank_name: Optional[str] = None
    transfer_reference: Optional[str] = None
    notes: Optional[str] = None


class ProductCorrectionRequest(ReasonPayload):
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    marca: Optional[str] = Field(None, min_length=1, max_length=100)
    modelo: Optional[str] = Field(None, min_length=1, max_length=150)
    color: Optional[str] = Field(None, max_length=100)
    capacidad: Optional[str] = Field(None, max_length=50)
    precio: Optional[float] = Field(None, ge=0)
    costo: Optional[float] = Field(None, ge=0)
    activo: Optional[bool] = None

    @field_validator("sku", "nombre", "marca", "modelo", mode="before")
    @classmethod
    def normalize_required_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("El campo no puede quedar vacío")
        return cleaned

    @field_validator("color", "capacidad", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class StockImeiIssue(BaseModel):
    product_id: int
    product_name: str
    location_id: int
    location_name: Optional[str] = None
    stock_disponible: int
    imeis_disponibles: int
    difference: int
    severity: str


class StockImeiDiagnosticsResponse(BaseModel):
    issues: list[StockImeiIssue]
    total_issues: int


class UserActiveRequest(ReasonPayload):
    is_active: bool


class SuperAdminAlert(BaseModel):
    id: str
    severity: str
    category: str
    title: str
    detail: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    location_id: Optional[int] = None
    created_at: datetime


def _json_load(value: Optional[str]) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def _serialize_stock(stock: Stock | None) -> dict[str, Any] | None:
    if not stock:
        return None
    return {
        "id": stock.id,
        "product_id": stock.product_id,
        "location_id": stock.location_id,
        "cantidad_disponible": stock.cantidad_disponible,
        "cantidad_reservada": stock.cantidad_reservada,
        "cantidad_defectuosa": stock.cantidad_defectuosa,
    }


def _serialize_audit(row: AuditLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "username": row.username,
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "location_id": row.location_id,
        "before_data": _json_load(row.before_data),
        "after_data": _json_load(row.after_data),
        "metadata": _json_load(row.metadata_json),
        "created_at": row.created_at,
    }


def _serialize_stock_history(row: StockHistory) -> dict[str, Any]:
    return {
        "id": row.id,
        "product_id": row.product_id,
        "product_name": row.product.nombre if row.product else None,
        "location_id": row.location_id,
        "location_name": row.location.nombre if row.location else None,
        "tipo_cambio": row.tipo_cambio,
        "cantidad": row.cantidad,
        "stock_anterior": row.stock_anterior,
        "stock_nuevo": row.stock_nuevo,
        "referencia_id": row.referencia_id,
        "referencia_tipo": row.referencia_tipo,
        "notas": row.notas,
        "usuario": row.usuario,
        "created_at": row.created_at,
    }


def _serialize_imei_history(row: IMEIHistory) -> dict[str, Any]:
    return {
        "id": row.id,
        "imei": row.imei,
        "product_id": row.product_id,
        "product_name": row.product.nombre if row.product else None,
        "location_id": row.location_id,
        "location_name": row.location.nombre if row.location else None,
        "event_type": row.event_type,
        "reference_id": row.reference_id,
        "reference_type": row.reference_type,
        "notes": row.notes,
        "created_by": row.created_by,
        "created_at": row.created_at,
    }


def _ensure_not_last_super_admin(db: Session, target_user: User) -> None:
    if not target_user.is_superuser:
        return
    active_superadmins = db.query(func.count(User.id)).filter(User.is_superuser == True, User.is_active == True).scalar() or 0
    if active_superadmins <= 1:
        raise HTTPException(status_code=400, detail="No se puede dejar el sistema sin Super Admin activo")


def _get_stock_imei_issues(db: Session) -> list[StockImeiIssue]:
    rows = (
        db.query(
            Stock,
            Product.nombre.label("product_name"),
        )
        .join(Product, Product.id == Stock.product_id)
        .filter(Product.is_serialized == True, Product.activo == True)
        .all()
    )

    issues: list[StockImeiIssue] = []
    for stock, product_name in rows:
        imei_count = (
            db.query(func.count(ProductIMEI.id))
            .filter(
                ProductIMEI.product_id == stock.product_id,
                ProductIMEI.location_id == stock.location_id,
                ProductIMEI.vendido == False,
                ProductIMEI.transfer_id.is_(None),
            )
            .scalar()
            or 0
        )
        stock_available = max(int(stock.cantidad_disponible or 0) - int(stock.cantidad_reservada or 0), 0)
        difference = stock_available - int(imei_count)
        if difference == 0:
            continue
        issues.append(
            StockImeiIssue(
                product_id=stock.product_id,
                product_name=product_name,
                location_id=stock.location_id,
                location_name=stock.location.nombre if stock.location else None,
                stock_disponible=stock_available,
                imeis_disponibles=int(imei_count),
                difference=difference,
                severity="alta" if abs(difference) > 1 else "media",
            )
        )
    return issues


@router.get("/diagnostics/stock-imeis", response_model=StockImeiDiagnosticsResponse)
def stock_imei_diagnostics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    issues = _get_stock_imei_issues(db)
    return StockImeiDiagnosticsResponse(issues=issues, total_issues=len(issues))


@router.get("/audit-logs")
def list_super_admin_audit_logs(
    username: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    super_admin_only: bool = Query(True),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    query = db.query(AuditLog)
    if super_admin_only:
        query = query.filter(AuditLog.action.ilike("super_admin.%"))
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username.strip()}%"))
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action.strip()}%"))
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)
    if location_id is not None:
        query = query.filter(AuditLog.location_id == location_id)
    if start_date:
        query = query.filter(AuditLog.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        parsed_end = datetime.fromisoformat(end_date)
        if len(end_date) == 10:
            parsed_end = parsed_end + timedelta(days=1)
            query = query.filter(AuditLog.created_at < parsed_end)
        else:
            query = query.filter(AuditLog.created_at <= parsed_end)

    rows = query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    return {"items": [_serialize_audit(row) for row in rows], "total": len(rows)}


@router.get("/entity-history")
def entity_history(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    imei: Optional[str] = Query(None),
    limit: int = Query(80, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    audit_query = db.query(AuditLog)
    if entity_type:
        audit_query = audit_query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        audit_query = audit_query.filter(AuditLog.entity_id == entity_id)
    if location_id is not None:
        audit_query = audit_query.filter(AuditLog.location_id == location_id)

    stock_query = db.query(StockHistory)
    if product_id is not None:
        stock_query = stock_query.filter(StockHistory.product_id == product_id)
    if location_id is not None:
        stock_query = stock_query.filter(StockHistory.location_id == location_id)
    if entity_type and entity_id is not None:
        referencia_map = {
            "order": ["order", "order_cancelled", "order_update", "order_finalized", "order_validated"],
            "stock_transfer": ["transfer", "transfer_pending", "transfer_rejected", "transfer_cancelled", "transfer_partial"],
            "stock": ["super_admin_panel", "manual_adjustment", "adjustment"],
        }
        refs = referencia_map.get(entity_type)
        if refs:
            stock_query = stock_query.filter(StockHistory.referencia_id == entity_id, StockHistory.referencia_tipo.in_(refs))

    imei_query = db.query(IMEIHistory)
    if imei:
        imei_query = imei_query.filter(IMEIHistory.imei == imei.strip())
    if product_id is not None:
        imei_query = imei_query.filter(IMEIHistory.product_id == product_id)
    if location_id is not None:
        imei_query = imei_query.filter(IMEIHistory.location_id == location_id)
    if entity_type and entity_id is not None:
        reference_type = "stock_transfer" if entity_type == "stock_transfer" else entity_type
        imei_query = imei_query.filter(IMEIHistory.reference_type == reference_type, IMEIHistory.reference_id == entity_id)

    return {
        "audit_logs": [_serialize_audit(row) for row in audit_query.order_by(desc(AuditLog.created_at)).limit(limit).all()],
        "stock_history": [_serialize_stock_history(row) for row in stock_query.order_by(desc(StockHistory.created_at)).limit(limit).all()],
        "imei_history": [_serialize_imei_history(row) for row in imei_query.order_by(desc(IMEIHistory.created_at)).limit(limit).all()],
    }


@router.get("/alerts")
def super_admin_alerts(
    stale_transfer_days: int = Query(2, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    alerts: list[SuperAdminAlert] = []
    now = datetime.now(UTC)

    bad_stock_rows = db.query(Stock).filter(
        or_(Stock.cantidad_disponible < 0, Stock.cantidad_reservada < 0, Stock.cantidad_reservada > Stock.cantidad_disponible)
    ).all()
    for stock in bad_stock_rows:
        alerts.append(SuperAdminAlert(
            id=f"stock-{stock.id}",
            severity="alta",
            category="stock",
            title="Stock inconsistente",
            detail=f"{stock.product.nombre if stock.product else 'Producto'} tiene disponible {stock.cantidad_disponible} y reservado {stock.cantidad_reservada}.",
            entity_type="stock",
            entity_id=stock.id,
            location_id=stock.location_id,
            created_at=now,
        ))

    for issue in _get_stock_imei_issues(db):
        alerts.append(SuperAdminAlert(
            id=f"imei-{issue.product_id}-{issue.location_id}",
            severity=issue.severity,
            category="imei_stock",
            title="Diferencia stock/IMEI",
            detail=f"{issue.product_name}: stock libre {issue.stock_disponible}, IMEIs disponibles {issue.imeis_disponibles}.",
            entity_type="product",
            entity_id=issue.product_id,
            location_id=issue.location_id,
            created_at=now,
        ))

    threshold = now - timedelta(days=stale_transfer_days)
    stale_transfers = db.query(StockTransfer).filter(StockTransfer.estado == "pendiente", StockTransfer.created_at <= threshold).all()
    for transfer in stale_transfers:
        alerts.append(SuperAdminAlert(
            id=f"transfer-{transfer.id}",
            severity="media",
            category="transfer",
            title="Transferencia pendiente antigua",
            detail=f"Transferencia #{transfer.id} de {transfer.product.nombre if transfer.product else 'producto'} lleva más de {stale_transfer_days} día(s) pendiente.",
            entity_type="stock_transfer",
            entity_id=transfer.id,
            location_id=transfer.from_location_id,
            created_at=transfer.created_at,
        ))

    denied_since = now - timedelta(hours=24)
    denied_attempts = db.query(AuditLog).filter(
        AuditLog.action == "super_admin.access.denied",
        AuditLog.created_at >= denied_since,
    ).order_by(desc(AuditLog.created_at)).limit(10).all()
    for attempt in denied_attempts:
        alerts.append(SuperAdminAlert(
            id=f"denied-{attempt.id}",
            severity="alta",
            category="security",
            title="Intento denegado al panel Super Admin",
            detail=f"{attempt.username or 'Usuario'} intentó acceder al panel en las últimas 24 horas.",
            entity_type="access",
            entity_id=attempt.id,
            location_id=attempt.location_id,
            created_at=attempt.created_at,
        ))

    return {"items": [alert.model_dump() for alert in alerts], "total": len(alerts)}


@router.get("/users")
def super_admin_users(
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    query = db.query(User)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(or_(User.username.ilike(like), User.full_name.ilike(like), User.email.ilike(like)))
    users = query.order_by(desc(User.created_at)).limit(limit).all()
    items = []
    for user in users:
        last_action = db.query(AuditLog).filter(AuditLog.user_id == user.id).order_by(desc(AuditLog.created_at)).first()
        action_count = db.query(func.count(AuditLog.id)).filter(AuditLog.user_id == user.id).scalar() or 0
        items.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "role_id": user.role_id,
            "role_name": user.role.name if user.role else None,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "audit_action_count": int(action_count),
            "last_action_at": last_action.created_at if last_action else None,
            "last_action": last_action.action if last_action else None,
        })
    return {"items": items, "total": len(items)}


@router.post("/users/{user_id}/active")
def set_user_active_status(
    user_id: int,
    payload: UserActiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")
    if not payload.is_active:
        _ensure_not_last_super_admin(db, user)
    before = {"is_active": user.is_active}
    user.is_active = payload.is_active
    log_audit_event(
        db,
        action="super_admin.user.active_status",
        entity_type="user",
        entity_id=user.id,
        user=current_user,
        before_data=before,
        after_data={"is_active": user.is_active},
        metadata={"reason": payload.reason},
    )
    db.commit()
    return {"ok": True, "user_id": user.id, "is_active": user.is_active}


@router.post("/users/{user_id}/reset-role")
def reset_user_role(
    user_id: int,
    payload: ReasonPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes resetear tu propio rol")
    _ensure_not_last_super_admin(db, user)
    guest_role = db.query(Role).filter(func.lower(Role.name).in_(["invitado", "guest"])).first()
    before = {"role_id": user.role_id, "role_name": user.role.name if user.role else None, "is_superuser": user.is_superuser}
    user.role_id = guest_role.id if guest_role else None
    user.is_superuser = False
    log_audit_event(
        db,
        action="super_admin.user.reset_role",
        entity_type="user",
        entity_id=user.id,
        user=current_user,
        before_data=before,
        after_data={"role_id": user.role_id, "role_name": guest_role.name if guest_role else None, "is_superuser": user.is_superuser},
        metadata={"reason": payload.reason},
    )
    db.commit()
    return {"ok": True, "user_id": user.id}


@router.post("/audit-logs/{audit_id}/revert")
def revert_audit_change(
    audit_id: int,
    payload: ReasonPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    audit = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    before = _json_load(audit.before_data)
    if not isinstance(before, dict):
        raise HTTPException(status_code=400, detail="Esta auditoría no tiene datos previos reversibles")

    if audit.action == "super_admin.stock.adjust":
        stock = db.query(Stock).filter(Stock.id == audit.entity_id).with_for_update().first()
        if not stock:
            raise HTTPException(status_code=404, detail="Stock no encontrado")
        current = _serialize_stock(stock)
        previous_available = int(stock.cantidad_disponible or 0)
        stock.cantidad_disponible = int(before.get("cantidad_disponible", 0))
        stock.cantidad_reservada = int(before.get("cantidad_reservada", 0))
        stock.cantidad_defectuosa = int(before.get("cantidad_defectuosa", 0))
        db.add(StockHistory(
            product_id=stock.product_id,
            location_id=stock.location_id,
            tipo_cambio="super_admin_revert",
            cantidad=stock.cantidad_disponible - previous_available,
            stock_anterior=previous_available,
            stock_nuevo=stock.cantidad_disponible,
            referencia_id=audit.id,
            referencia_tipo="super_admin_panel",
            notas=payload.reason,
            usuario=current_user.username,
        ))
        after = _serialize_stock(stock)
        entity_type = "stock"
        entity_id = stock.id
    elif audit.action == "super_admin.product.catalog_correction":
        product = db.query(Product).filter(Product.id == audit.entity_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        current = {"sku": product.sku, "nombre": product.nombre, "marca": product.marca, "modelo": product.modelo, "color": product.color, "capacidad": product.capacidad, "precio": float(product.precio or 0), "costo": float(product.costo or 0), "activo": product.activo}
        for field in ["sku", "nombre", "marca", "modelo", "color", "capacidad", "precio", "costo", "activo"]:
            if field in before:
                setattr(product, field, before[field])
        after = {"sku": product.sku, "nombre": product.nombre, "marca": product.marca, "modelo": product.modelo, "color": product.color, "capacidad": product.capacidad, "precio": float(product.precio or 0), "costo": float(product.costo or 0), "activo": product.activo}
        entity_type = "product"
        entity_id = product.id
    elif audit.action == "super_admin.order.payment_correction":
        order = db.query(Order).filter(Order.id == audit.entity_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        current = {"metodo_pago": order.metodo_pago, "payment_breakdown": order.payment_breakdown, "transfer_bank_name": order.transfer_bank_name, "transfer_reference": order.transfer_reference, "notes": order.notes}
        for field in ["metodo_pago", "payment_breakdown", "transfer_bank_name", "transfer_reference", "notes"]:
            if field in before:
                setattr(order, field, before[field])
        after = {"metodo_pago": order.metodo_pago, "payment_breakdown": order.payment_breakdown, "transfer_bank_name": order.transfer_bank_name, "transfer_reference": order.transfer_reference, "notes": order.notes}
        entity_type = "order"
        entity_id = order.id
    else:
        raise HTTPException(status_code=400, detail="Esta acción no tiene reversa automática segura")

    log_audit_event(
        db,
        action="super_admin.audit.revert",
        entity_type=entity_type,
        entity_id=entity_id,
        location_id=audit.location_id,
        user=current_user,
        before_data=current,
        after_data=after,
        metadata={"reason": payload.reason, "reverted_audit_id": audit.id, "reverted_action": audit.action},
    )
    db.commit()
    return {"ok": True, "reverted_audit_id": audit.id}


@router.post("/stock/adjust")
def adjust_stock(
    payload: StockAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    location = db.query(Location).filter(Location.id == payload.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")

    stock = (
        db.query(Stock)
        .filter(Stock.product_id == payload.product_id, Stock.location_id == payload.location_id)
        .with_for_update()
        .first()
    )
    before = _serialize_stock(stock)
    if not stock:
        stock = Stock(product_id=payload.product_id, location_id=payload.location_id)
        db.add(stock)
        db.flush()

    previous_available = int(stock.cantidad_disponible or 0)
    stock.cantidad_disponible = payload.cantidad_disponible
    stock.cantidad_reservada = payload.cantidad_reservada
    stock.cantidad_defectuosa = payload.cantidad_defectuosa

    db.add(
        StockHistory(
            product_id=payload.product_id,
            location_id=payload.location_id,
            tipo_cambio="super_admin_adjustment",
            cantidad=payload.cantidad_disponible - previous_available,
            stock_anterior=previous_available,
            stock_nuevo=payload.cantidad_disponible,
            referencia_tipo="super_admin_panel",
            notas=payload.reason,
            usuario=current_user.username,
        )
    )
    log_audit_event(
        db,
        action="super_admin.stock.adjust",
        entity_type="stock",
        entity_id=stock.id,
        location_id=payload.location_id,
        user=current_user,
        before_data=before,
        after_data=_serialize_stock(stock),
        metadata={"reason": payload.reason},
    )
    db.commit()
    db.refresh(stock)
    return _serialize_stock(stock)


@router.post("/orders/{order_id}/cancel")
def super_admin_cancel_order(
    order_id: int,
    payload: ReasonPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    from app.routers.orders import cancel_order

    return cancel_order(order_id=order_id, reason=f"SUPER ADMIN: {payload.reason}", db=db, current_user=current_user)


@router.post("/orders/{order_id}/payment-correction")
def correct_order_payment(
    order_id: int,
    payload: OrderPaymentCorrectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    before = {
        "metodo_pago": order.metodo_pago,
        "payment_breakdown": order.payment_breakdown,
        "transfer_bank_name": order.transfer_bank_name,
        "transfer_reference": order.transfer_reference,
        "notes": order.notes,
    }

    if payload.metodo_pago:
        order.metodo_pago = payload.metodo_pago.value
    if payload.payment_breakdown is not None:
        order.payment_breakdown = serialize_payment_breakdown(payload.payment_breakdown)
    if payload.transfer_bank_name is not None:
        order.transfer_bank_name = payload.transfer_bank_name.strip() or None
    if payload.transfer_reference is not None:
        order.transfer_reference = payload.transfer_reference.strip() or None
    if payload.notes:
        order.notes = f"{order.notes or ''} | CORRECCION SUPER ADMIN: {payload.notes}".strip()

    log_audit_event(
        db,
        action="super_admin.order.payment_correction",
        entity_type="order",
        entity_id=order.id,
        location_id=order.source_location_id,
        user=current_user,
        before_data=before,
        after_data={
            "metodo_pago": order.metodo_pago,
            "payment_breakdown": order.payment_breakdown,
            "transfer_bank_name": order.transfer_bank_name,
            "transfer_reference": order.transfer_reference,
            "notes": order.notes,
        },
        metadata={"reason": payload.reason},
    )
    db.commit()
    return {"ok": True, "order_id": order.id}


@router.patch("/products/{product_id}")
def correct_product_catalog(
    product_id: int,
    payload: ProductCorrectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if payload.sku and payload.sku != product.sku:
        existing = db.query(Product).filter(Product.sku == payload.sku, Product.id != product_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe otro producto con ese SKU")

    before = {
        "sku": product.sku,
        "nombre": product.nombre,
        "marca": product.marca,
        "modelo": product.modelo,
        "color": product.color,
        "capacidad": product.capacidad,
        "precio": float(product.precio or 0),
        "costo": float(product.costo or 0),
        "activo": product.activo,
    }

    for field in ["sku", "nombre", "marca", "modelo", "color", "capacidad", "precio", "costo", "activo"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(product, field, value)

    after = {
        "sku": product.sku,
        "nombre": product.nombre,
        "marca": product.marca,
        "modelo": product.modelo,
        "color": product.color,
        "capacidad": product.capacidad,
        "precio": float(product.precio or 0),
        "costo": float(product.costo or 0),
        "activo": product.activo,
    }

    log_audit_event(
        db,
        action="super_admin.product.catalog_correction",
        entity_type="product",
        entity_id=product.id,
        user=current_user,
        before_data=before,
        after_data=after,
        metadata={"reason": payload.reason},
    )
    db.commit()
    db.refresh(product)
    return {"ok": True, "product_id": product.id}


@router.post("/stock-transfers/{transfer_id}/cancel")
def super_admin_cancel_transfer(
    transfer_id: int,
    payload: ReasonPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser_audited),
):
    transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    if transfer.estado != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se pueden cancelar transferencias pendientes desde este panel")

    source_stock = (
        db.query(Stock)
        .filter(Stock.product_id == transfer.product_id, Stock.location_id == transfer.from_location_id)
        .with_for_update()
        .first()
    )
    if not source_stock:
        raise HTTPException(status_code=400, detail="Stock de origen no encontrado")

    before = {
        "estado": transfer.estado,
        "stock": _serialize_stock(source_stock),
        "imeis": [item.imei for item in db.query(ProductIMEI).filter(ProductIMEI.transfer_id == transfer.id).all()],
    }

    try:
        StockManager(db).release_reservation(
            stock=source_stock,
            quantity=int(transfer.cantidad or 0),
            transfer_id=transfer.id,
            notes=f"Cancelación Super Admin: {payload.reason}",
            user_id=current_user.username,
            is_rejection=True,
            tipo_cambio="transferencia_cancelada",
            referencia_tipo="transfer_cancelled",
        )
    except StockValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    transfer.estado = "cancelada"
    transfer.confirmed_at = datetime.now(UTC)
    transfer.confirmed_by = current_user.username
    transfer.rejection_reason = f"SUPER ADMIN: {payload.reason}"

    reserved_imeis = db.query(ProductIMEI).filter(ProductIMEI.transfer_id == transfer.id).all()
    for item in reserved_imeis:
        item.transfer_id = None
        db.add(IMEIHistory(
            imei=item.imei,
            product_id=item.product_id,
            location_id=item.location_id,
            event_type="super_admin_transfer_cancel",
            reference_id=transfer.id,
            reference_type="stock_transfer",
            notes=payload.reason,
            created_by=current_user.username,
        ))

    log_audit_event(
        db,
        action="super_admin.stock_transfer.cancel",
        entity_type="stock_transfer",
        entity_id=transfer.id,
        location_id=transfer.from_location_id,
        user=current_user,
        before_data=before,
        after_data={"estado": transfer.estado, "stock": _serialize_stock(source_stock)},
        metadata={"reason": payload.reason},
    )
    db.commit()
    return {"ok": True, "transfer_id": transfer.id}
