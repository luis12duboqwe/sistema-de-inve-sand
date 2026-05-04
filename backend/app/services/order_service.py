"""Servicio de alto nivel para operaciones de órdenes."""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Sequence
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    InteractionLog,
    Order,
    Profile,
    SalesProfile,
    User,
)
from app.schemas import OrderCreate
from app.services.stock_transaction_helper import (
    PreparedSaleItem,
    SalePreparationResult,
    StockTransactionHelper,
)
from app.utils.order_financing import compute_financing_from_payload
from app.utils.order_validators import (
    resolve_sales_profile,
    validate_location_and_phone,
)
from app.utils.stock_manager import StockManager

logger = logging.getLogger(__name__)


def normalize_transfer_reference(reference: Optional[str]) -> Optional[str]:
    """Normaliza referencia para comparación anti-duplicados.

    Reglas:
    - Trim
    - Uppercase
    - Solo alfanumérico (remueve espacios, guiones y símbolos)
    """
    if reference is None:
        return None
    raw = str(reference).strip().upper()
    if not raw:
        return None
    normalized = "".join(ch for ch in raw if ch.isalnum())
    return normalized or None


def ensure_unique_transfer_reference(
    db: Session,
    normalized_reference: Optional[str],
    *,
    exclude_order_id: Optional[int] = None,
) -> None:
    """Valida que la referencia de transferencia no exista en otra orden."""
    if not normalized_reference:
        return

    query = db.query(Order).filter(Order.transfer_reference_normalized == normalized_reference)
    if exclude_order_id is not None:
        query = query.filter(Order.id != exclude_order_id)

    duplicated_order = query.order_by(Order.created_at.desc()).first()
    if duplicated_order:
        created_label = duplicated_order.created_at.strftime("%d/%m/%Y %H:%M") if duplicated_order.created_at else "N/A"
        raise HTTPException(
            status_code=409,
            detail=(
                f"La referencia de transferencia ya fue usada en la orden #{duplicated_order.id} "
                f"({created_label}, cliente: {duplicated_order.customer_name})."
            ),
        )


def resolve_user_label(
    current_user: Optional[User],
    sales_profile: Optional[SalesProfile] = None,
    profile: Optional[Profile] = None,
    fallback: str = "Sistema",
) -> str:
    """Devuelve un identificador legible para logs/auditoría."""
    if current_user and getattr(current_user, "username", None):
        return str(current_user.username)  # type: ignore[attr-defined]
    if sales_profile and getattr(sales_profile, "name", None):
        return str(sales_profile.name)
    if profile and getattr(profile, "name", None):
        return str(profile.name)
    return fallback


class OrderService:
    """Orquesta la creación de órdenes aplicando las validaciones V2.0."""

    def __init__(
        self,
        db: Session,
        *,
        stock_helper: Optional[StockTransactionHelper] = None,
    ) -> None:
        self.db = db
        self.stock_helper = stock_helper or StockTransactionHelper(db)
        self.stock_manager: StockManager = self.stock_helper.stock_manager

    def create_order(
        self,
        order: OrderCreate,
        *,
        current_user: Optional[User] = None,
    ) -> Order:
        """Crea una orden completa y devuelve el modelo persistido."""
        try:
            (
                sales_profile,
                legacy_profile,
                sales_profile_id_for_order,
                profile_id_for_order,
            ) = resolve_sales_profile(
                db=self.db,
                sales_profile_slug=order.sales_profile_slug,
                profile_slug=order.profile_slug,
            )

            location, customer_phone_str = validate_location_and_phone(
                db=self.db,
                source_location_id=order.source_location_id,
                customer_phone=order.customer_phone,
            )
            location_id_value = int(getattr(location, "id", 0) or 0)

            if not order.items:
                raise HTTPException(status_code=400, detail="La orden debe contener al menos un producto")

            user_identifier = resolve_user_label(current_user, sales_profile, legacy_profile)

            transfer_bank_name, transfer_reference, transfer_reference_normalized = self._resolve_transfer_payment_data(order)
            ensure_unique_transfer_reference(
                self.db,
                transfer_reference_normalized,
            )

            sale_batch = self._prepare_sale_batch(
                items_payload=order.items,
                location_id=location_id_value,
                allow_pending_imei=False,
            )
            self._ensure_not_only_gifts(sale_batch)

            trade_in_total = self.stock_helper.process_trade_ins(
                trade_ins_payload=order.trade_ins,
                db_order=None,
                profile_id_for_order=profile_id_for_order,
                source_location_id=location_id_value,
                user_label=user_identifier,
            )

            order_totals = self.stock_helper.calculate_order_totals(
                sale_result=sale_batch,
                trade_in_total=trade_in_total,
            )
            total_final, financing_details_json = compute_financing_from_payload(
                db=self.db,
                financing_data=order.financing_data,
                metodo_pago=order.metodo_pago,
                total_after_tradeins=order_totals.total_after_trade_ins,
                trade_in_total=order_totals.trade_in_total,
            )

            db_order = self._create_order_record(
                order=order,
                profile_id_for_order=profile_id_for_order,
                sales_profile_id_for_order=sales_profile_id_for_order,
                customer_phone=customer_phone_str,
                total=total_final,
                financing_details_json=financing_details_json,
                transfer_bank_name=transfer_bank_name,
                transfer_reference=transfer_reference,
                transfer_reference_normalized=transfer_reference_normalized,
            )

            if order.trade_ins:
                self.stock_helper.process_trade_ins(
                    trade_ins_payload=order.trade_ins,
                    db_order=db_order,
                    profile_id_for_order=profile_id_for_order,
                    source_location_id=location_id_value,
                    user_label=user_identifier,
                )

            self._persist_order_items(
                db_order=db_order,
                prepared_items=sale_batch.items,
                order_payload=order,
                user_identifier=user_identifier,
            )

            self._link_ai_interaction(
                db_order,
                sales_profile_id_for_order=sales_profile_id_for_order,
                customer_phone=order.customer_phone,
            )

            self.db.commit()
            self.db.refresh(db_order)
            for item in db_order.items:
                self.db.refresh(item)

            return db_order
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:  # noqa: BLE001
            self.db.rollback()
            logger.exception("Error interno al crear orden")
            raise HTTPException(status_code=500, detail=f"Error al crear la orden: {exc}")

    def _prepare_sale_batch(
        self,
        *,
        items_payload: Sequence[object],
        location_id: int,
        allow_pending_imei: bool,
    ) -> SalePreparationResult:
        return self.stock_helper.prepare_sale_batch(
            items_payload=items_payload,
            location_id=location_id,
            allow_pending_imei=allow_pending_imei,
        )

    def _ensure_not_only_gifts(
        self,
        sale_batch: SalePreparationResult,
    ) -> None:
        if sale_batch.total == Decimal("0.00") and sale_batch.has_items:
            if not sale_batch.has_regular_items:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "La orden debe tener al menos un producto con valor. "
                        "No se pueden crear órdenes solo con regalos/promociones."
                    ),
                )

    def _create_order_record(
        self,
        *,
        order: OrderCreate,
        profile_id_for_order: Optional[int],
        sales_profile_id_for_order: Optional[int],
        customer_phone: Optional[str],
        total: Decimal,
        financing_details_json: Optional[str],
        transfer_bank_name: Optional[str],
        transfer_reference: Optional[str],
        transfer_reference_normalized: Optional[str],
    ) -> Order:
        db_order = Order(
            profile_id=profile_id_for_order,
            sales_profile_id=sales_profile_id_for_order,
            source_location_id=order.source_location_id,
            customer_name=order.customer_name,
            customer_phone=customer_phone,
            canal=order.canal,
            metodo_pago=order.metodo_pago,
            transfer_bank_name=transfer_bank_name,
            transfer_reference=transfer_reference,
            transfer_reference_normalized=transfer_reference_normalized,
            total=total,
            financing_details=financing_details_json,
            estado="pendiente",
            notes=order.notes,
            delivery_date=order.delivery_date,
        )
        self.db.add(db_order)
        self.db.flush()
        return db_order

    def _resolve_transfer_payment_data(
        self,
        order: OrderCreate,
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        if order.metodo_pago != "transferencia":
            return None, None, None

        bank_name = (order.transfer_bank_name or "").strip()
        transfer_reference = (order.transfer_reference or "").strip()

        if not bank_name:
            raise HTTPException(
                status_code=400,
                detail="Debe indicar el banco cuando el método de pago es transferencia",
            )

        if not transfer_reference:
            raise HTTPException(
                status_code=400,
                detail="Debe indicar el número de referencia cuando el método de pago es transferencia",
            )

        normalized = normalize_transfer_reference(transfer_reference)
        if not normalized:
            raise HTTPException(
                status_code=400,
                detail="El número de referencia de transferencia no es válido",
            )

        return bank_name, transfer_reference, normalized

    def _persist_order_items(
        self,
        *,
        db_order: Order,
        prepared_items: List[PreparedSaleItem],
        order_payload: OrderCreate,
        user_identifier: str,
    ) -> None:
        self.stock_helper.persist_prepared_sale_items(
            db_order=db_order,
            prepared_items=prepared_items,
            customer_name=order_payload.customer_name,
            canal=order_payload.canal,
            user_identifier=user_identifier,
        )


    def _link_ai_interaction(
        self,
        db_order: Order,
        *,
        sales_profile_id_for_order: Optional[int],
        customer_phone: Optional[str],
    ) -> None:
        if not (sales_profile_id_for_order and customer_phone):
            return

        try:
            normalized_phone = "".join(filter(str.isdigit, str(customer_phone)))
            customer = (
                self.db.query(Customer)
                .filter(Customer.phone_number == normalized_phone)
                .first()
            )
            if not customer:
                return

            last_interaction = (
                self.db.query(InteractionLog)
                .filter(
                    InteractionLog.customer_id == customer.id,
                    InteractionLog.sales_profile_id == sales_profile_id_for_order,
                    InteractionLog.converted_order_id == None,
                )
                .order_by(InteractionLog.created_at.desc())
                .first()
            )

            if last_interaction:
                last_interaction.converted_order_id = db_order.id
                self.db.add(last_interaction)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error linking order to interaction: %s", exc)