"""Helpers reutilizables para operaciones de stock con bloqueo pesimista."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, cast

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    IMEIHistory,
    Order,
    OrderItem,
    Product,
    ProductIMEI,
    Return,
    ReturnItem,
    Stock,
    StockHistory,
    TradeIn,
)
from app.utils.order_tradeins import compute_trade_in_total
from app.utils.stock_manager import StockManager, StockValidationError


@dataclass(slots=True)
class PreparedSaleItem:
    product: Product
    stock: Stock
    cantidad: int
    precio_unitario: Decimal
    es_regalo_promocion: bool
    imeis_to_sell: List[ProductIMEI]


@dataclass(slots=True)
class SalePreparationResult:
    total: Decimal
    gifts_total: Decimal
    items: List[PreparedSaleItem]

    @property
    def has_items(self) -> bool:
        return bool(self.items)

    @property
    def has_regular_items(self) -> bool:
        return any(not item.es_regalo_promocion for item in self.items)


@dataclass(slots=True)
class PreparedReturnItem:
    product: Product
    order_item: OrderItem
    quantity: int
    condition: Optional[str]
    action: Optional[str]
    imei_value: Optional[str]
    imeis_to_release: List[ProductIMEI]


@dataclass(slots=True)
class OrderTotals:
    subtotal: Decimal
    trade_in_total: Decimal
    total_after_trade_ins: Decimal


class StockTransactionHelper:
    """Orquesta operaciones complejas de stock e IMEIs con bloqueos atómicos."""

    def __init__(self, db: Session, *, stock_manager: Optional[StockManager] = None) -> None:
        self.db = db
        self.stock_manager = stock_manager or StockManager(db)

    def prepare_sale_items(
        self,
        *,
        items_payload: Sequence[Any],
        location_id: int,
        allow_pending_imei: bool = False,
    ) -> Tuple[Decimal, List[PreparedSaleItem]]:
        """Normaliza los ítems de venta bloqueando stock e IMEIs necesarios."""

        if not items_payload:
            raise HTTPException(status_code=400, detail="Debe proporcionar al menos un ítem a vender")

        total = Decimal("0.00")
        prepared: List[PreparedSaleItem] = []

        for raw_item in items_payload:
            product_id_raw = self._get_attr(raw_item, "product_id")
            if product_id_raw is None:
                raise HTTPException(status_code=400, detail="Cada ítem debe incluir product_id")

            try:
                product_id = int(product_id_raw)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="product_id inválido") from exc

            quantity_value = self._get_attr(raw_item, "cantidad")
            if quantity_value is None:
                quantity_value = self._get_attr(raw_item, "quantity", 0)
            quantity = int(quantity_value or 0)
            if quantity <= 0:
                raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0")

            precio_custom = self._get_attr(raw_item, "precio_unitario")
            es_regalo = bool(self._get_attr(raw_item, "es_regalo_promocion", False))
            imeis_payload = self._get_attr(raw_item, "imeis")

            imeis_requested: Optional[List[str]] = None
            if imeis_payload:
                if isinstance(imeis_payload, (list, tuple, set)):
                    iterable_payload = cast(Iterable[object], imeis_payload)
                    imeis_requested = [
                        cleaned_value
                        for cleaned_value in (str(imei_entry).strip() for imei_entry in iterable_payload)
                        if cleaned_value
                    ]
                else:
                    cleaned = str(imeis_payload).strip()
                    imeis_requested = [cleaned] if cleaned else None

            product, stock, imeis_to_sell = self.stock_manager.validate_and_lock_stock(
                product_id=product_id,
                location_id=location_id,
                quantity=quantity,
                imeis_requested=imeis_requested,
                allow_pending_imei=allow_pending_imei,
                operation_type="sale",
            )

            precio_unitario = self._resolve_unit_price(product.precio, precio_custom)

            if not es_regalo:
                total += precio_unitario * quantity

            prepared.append(
                PreparedSaleItem(
                    product=product,
                    stock=stock,
                    cantidad=quantity,
                    precio_unitario=precio_unitario,
                    es_regalo_promocion=es_regalo,
                    imeis_to_sell=imeis_to_sell,
                )
            )

        return total, prepared

    def prepare_sale_batch(
        self,
        *,
        items_payload: Sequence[Any],
        location_id: int,
        allow_pending_imei: bool = False,
    ) -> SalePreparationResult:
        """Devuelve un resumen estructurado con totales y items preparados."""

        total, prepared_items = self.prepare_sale_items(
            items_payload=items_payload,
            location_id=location_id,
            allow_pending_imei=allow_pending_imei,
        )

        gifts_total = sum(
            (
                item.precio_unitario * item.cantidad
                for item in prepared_items
                if item.es_regalo_promocion
            ),
            start=Decimal("0.00"),
        )

        return SalePreparationResult(total=total, gifts_total=gifts_total, items=prepared_items)

    def calculate_order_totals(
        self,
        *,
        sale_result: SalePreparationResult,
        trade_in_total: Decimal,
    ) -> OrderTotals:
        """Normaliza totales considerando retomas y evita números negativos."""

        normalized_trade_in = trade_in_total if trade_in_total > Decimal("0.00") else Decimal("0.00")
        total_after_trade_ins = sale_result.total - normalized_trade_in
        if total_after_trade_ins < Decimal("0.00"):
            total_after_trade_ins = Decimal("0.00")

        return OrderTotals(
            subtotal=sale_result.total,
            trade_in_total=normalized_trade_in,
            total_after_trade_ins=total_after_trade_ins,
        )

    def persist_prepared_sale_items(
        self,
        *,
        db_order: Order,
        prepared_items: Sequence[PreparedSaleItem],
        customer_name: Optional[str],
        canal: Optional[str],
        user_identifier: str,
    ) -> None:
        """Crea OrderItems, marca IMEIs vendidos y ajusta stock en una sola rutina."""

        customer_label = (customer_name or "Cliente").strip() or "Cliente"
        canal_label = canal or "canal_desconocido"
        notes_template = f"Venta a {customer_label} - Canal: {canal_label}"
        order_id_value = int(getattr(db_order, "id", 0) or 0)

        for item_data in prepared_items:
            db_order_item = OrderItem(
                order_id=db_order.id,
                product_id=item_data.product.id,
                cantidad=item_data.cantidad,
                precio_unitario=item_data.precio_unitario,
                es_regalo_promocion=item_data.es_regalo_promocion,
            )
            self.db.add(db_order_item)

            if item_data.imeis_to_sell:
                self.stock_manager.mark_imeis_as_sold(
                    imeis=item_data.imeis_to_sell,
                    order_id=order_id_value,
                    notes=f"Venta en orden #{order_id_value}",
                    user_id=user_identifier,
                )

            try:
                self.stock_manager.decrease_stock(
                    stock=item_data.stock,
                    quantity=item_data.cantidad,
                    operation_type="venta",
                    notes=notes_template,
                    user_id=user_identifier,
                    order_id=order_id_value,
                )
            except StockValidationError as exc:  # Seguridad adicional ante condiciones de carrera
                raise HTTPException(status_code=409, detail=str(exc)) from exc

    def process_trade_ins(
        self,
        *,
        trade_ins_payload: Optional[Sequence[Any]],
        db_order: Optional[Order],
        profile_id_for_order: Optional[int],
        source_location_id: int,
        user_label: str,
    ) -> Decimal:
        """Procesa retomas tanto para cálculo de totales como para persistencia."""

        trade_in_total = compute_trade_in_total(trade_ins_payload)
        if not trade_ins_payload:
            return trade_in_total

        if db_order is None:
            return trade_in_total

        order_id_value = int(getattr(db_order, "id", 0) or 0)

        for trade_in_item in trade_ins_payload:
            valor_estimado = self._safe_decimal(getattr(trade_in_item, "valor_estimado", 0))
            db_trade_in = TradeIn(
                order_id=order_id_value,
                marca=getattr(trade_in_item, "marca", ""),
                modelo=getattr(trade_in_item, "modelo", ""),
                color=getattr(trade_in_item, "color", None),
                capacidad=getattr(trade_in_item, "capacidad", None),
                imei=getattr(trade_in_item, "imei", None),
                condicion=getattr(trade_in_item, "condicion", "pendiente"),
                valor_estimado=valor_estimado,
                notas=getattr(trade_in_item, "notas", None),
            )
            self.db.add(db_trade_in)

            trade_in_product = self._get_or_create_trade_in_product(
                trade_in_item=trade_in_item,
                profile_id_for_order=profile_id_for_order,
                valor_estimado=valor_estimado,
            )
            trade_in_product_id = int(getattr(trade_in_product, "id", 0) or 0)

            _, stock_anterior = self._ensure_trade_in_stock_entry(
                product=trade_in_product,
                location_id=source_location_id,
            )

            imei_value_raw = getattr(trade_in_item, "imei", None)
            if imei_value_raw:
                imei_value = str(imei_value_raw).strip()
                if imei_value:
                    self._upsert_trade_in_imei(
                        imei_value=imei_value,
                        product_id=trade_in_product_id,
                        location_id=source_location_id,
                        order_id=order_id_value,
                        user_label=user_label,
                    )

            stock_history_retoma = StockHistory(
                product_id=trade_in_product_id,
                location_id=source_location_id,
                tipo_cambio="retoma",
                cantidad=1,
                stock_anterior=stock_anterior,
                stock_nuevo=stock_anterior + 1,
                referencia_id=order_id_value,
                referencia_tipo="order",
                notas=(
                    f"Ingreso por retoma de {getattr(trade_in_item, 'marca', 'Equipo')} "
                    f"{getattr(trade_in_item, 'modelo', '').strip()}"
                ).strip(),
                usuario=user_label,
            )
            self.db.add(stock_history_retoma)

        return trade_in_total

    def prepare_return_items(
        self,
        *,
        order: Order,
        items_payload: Sequence[Any],
    ) -> List[PreparedReturnItem]:
        """Valida devoluciones asegurando cantidades e IMEIs consistentes."""

        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")

        if not order.items:
            order_items = self.db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        else:
            order_items = list(order.items)

        if not order_items:
            raise HTTPException(status_code=400, detail="La orden no tiene productos registrados")

        order_id_value = int(getattr(order, "id", 0) or 0)

        order_items_map: Dict[int, OrderItem] = {}
        for item in order_items:
            item_product_id = getattr(item, "product_id", None)
            if item_product_id is None:
                continue
            order_items_map[int(item_product_id)] = item

        previous_returns = (
            self.db.query(ReturnItem)
            .join(Return, ReturnItem.return_id == Return.id)
            .filter(Return.order_id == order.id)
            .all()
        )

        returned_quantities: Dict[int, int] = {}
        returned_imeis: Set[str] = set()
        for prev in previous_returns:
            prev_product_id = getattr(prev, "product_id", None)
            if prev_product_id is None:
                continue
            product_key = int(prev_product_id)
            prev_quantity = int(getattr(prev, "quantity", 0) or 0)
            returned_quantities[product_key] = returned_quantities.get(product_key, 0) + prev_quantity
            prev_imei = getattr(prev, "imei", None)
            if prev_imei:
                returned_imeis.add(str(prev_imei))

        prepared_items: List[PreparedReturnItem] = []

        for raw_item in items_payload:
            product_id_raw = self._get_attr(raw_item, "product_id")
            quantity = int(self._get_attr(raw_item, "quantity", 0) or 0)
            condition_raw = self._get_attr(raw_item, "condition")
            action_raw = self._get_attr(raw_item, "action")
            imei_value_raw = self._get_attr(raw_item, "imei")

            if product_id_raw is None:
                raise HTTPException(status_code=400, detail="Cada devolución requiere un product_id válido")

            if quantity <= 0:
                raise HTTPException(status_code=400, detail="La cantidad a devolver debe ser mayor a 0")

            try:
                product_id = int(product_id_raw)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="product_id inválido") from exc

            order_item = order_items_map.get(product_id)
            if not order_item:
                raise HTTPException(
                    status_code=400,
                    detail=f"El producto {product_id} no pertenece a la orden #{order.id}",
                )

            product = order_item.product
            if not product:
                product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado")

            prev_qty = returned_quantities.get(product_id, 0)
            order_item_quantity = int(getattr(order_item, "cantidad", 0) or 0)
            if prev_qty + quantity > order_item_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Cantidad a devolver ({prev_qty + quantity}) excede la comprada ({order_item_quantity}) "
                        f"para producto {product_id}"
                    ),
                )
            returned_quantities[product_id] = prev_qty + quantity

            condition = condition_raw.value if hasattr(condition_raw, "value") else condition_raw
            action = action_raw.value if hasattr(action_raw, "value") else action_raw

            imeis_to_release: List[ProductIMEI] = []
            imei_value: Optional[str] = None
            is_serialized_product = bool(getattr(product, "is_serialized", False))
            product_sku = getattr(product, "sku", product_id)

            if imei_value_raw:
                imei_value = str(imei_value_raw).strip()
                if imei_value in returned_imeis:
                    raise HTTPException(
                        status_code=400,
                        detail=f"El IMEI {imei_value} ya fue devuelto previamente",
                    )

                imei_record = (
                    self.db.query(ProductIMEI)
                    .filter(ProductIMEI.imei == imei_value)
                    .with_for_update()
                    .first()
                )

                if not imei_record:
                    raise HTTPException(status_code=400, detail=f"IMEI {imei_value} no existe en inventario")

                imei_order_id = int(getattr(imei_record, "order_id", 0) or 0)
                vendido_flag = bool(getattr(imei_record, "vendido", False))
                if imei_order_id != order_id_value or not vendido_flag:
                    raise HTTPException(
                        status_code=400,
                        detail=f"IMEI {imei_value} no pertenece a la orden #{order_id_value} o ya fue liberado",
                    )

                imeis_to_release.append(imei_record)
                returned_imeis.add(imei_value)
            elif is_serialized_product:
                raise HTTPException(
                    status_code=400,
                    detail=f"El producto {product_sku} es serializado. Debe proporcionar el IMEI para la devolución.",
                )

            prepared_items.append(
                PreparedReturnItem(
                    product=product,
                    order_item=order_item,
                    quantity=quantity,
                    condition=condition,
                    action=action,
                    imei_value=imei_value,
                    imeis_to_release=imeis_to_release,
                )
            )

        return prepared_items

    @staticmethod
    def _get_attr(item: Any, field: str, default: Any = None) -> Any:
        if hasattr(item, field):
            return getattr(item, field)
        if isinstance(item, Mapping):
            mapping_item = cast(Mapping[str, Any], item)
            return mapping_item.get(field, default)
        return default

    def _get_or_create_trade_in_product(
        self,
        *,
        trade_in_item: Any,
        profile_id_for_order: Optional[int],
        valor_estimado: Decimal,
    ) -> Product:
        query = self.db.query(Product).filter(
            Product.marca == getattr(trade_in_item, "marca", None),
            Product.modelo == getattr(trade_in_item, "modelo", None),
            Product.condicion == getattr(trade_in_item, "condicion", None),
            Product.activo == True,  # noqa: E712
        )
        color_value = getattr(trade_in_item, "color", None)
        if color_value:
            query = query.filter(Product.color == color_value)
        capacity_value = getattr(trade_in_item, "capacidad", None)
        if capacity_value:
            query = query.filter(Product.capacidad == capacity_value)

        existing_product = query.first()
        if existing_product:
            return existing_product

        nombre_producto = self._build_trade_in_product_name(trade_in_item)
        precio_venta_attr = getattr(trade_in_item, "precio_venta", None)
        if precio_venta_attr is None:
            precio_publico = (valor_estimado or Decimal("0.00")) * Decimal("1.3")
        else:
            precio_publico = self._safe_decimal(precio_venta_attr)

        sku_suffix = getattr(trade_in_item, "imei", "") or uuid.uuid4().hex
        sku_token = sku_suffix[-6:] if len(sku_suffix) >= 6 else sku_suffix
        generated_sku = f"RET-{sku_token}-{uuid.uuid4().hex[:4]}"

        new_product = Product(
            sku=generated_sku,
            nombre=nombre_producto,
            categoria="pendiente_revision",
            marca=getattr(trade_in_item, "marca", None),
            modelo=getattr(trade_in_item, "modelo", None),
            color=color_value,
            capacidad=capacity_value,
            condicion=getattr(trade_in_item, "condicion", None),
            precio=precio_publico,
            costo=valor_estimado,
            moneda="HNL",
            activo=False,
            profile_id=profile_id_for_order,
            is_serialized=True,
        )
        self.db.add(new_product)
        self.db.flush()
        return new_product

    def _ensure_trade_in_stock_entry(
        self,
        *,
        product: Product,
        location_id: int,
    ) -> Tuple[Stock, int]:
        stock_record = (
            self.db.query(Stock)
            .filter(Stock.product_id == product.id, Stock.location_id == location_id)
            .with_for_update()
            .first()
        )

        if stock_record:
            previous = int(getattr(stock_record, "cantidad_disponible", 0) or 0)
            setattr(stock_record, "cantidad_disponible", previous + 1)
            return stock_record, previous

        stock_record = Stock(
            product_id=product.id,
            location_id=location_id,
            cantidad_disponible=1,
            cantidad_reservada=0,
        )
        self.db.add(stock_record)
        return stock_record, 0

    def _upsert_trade_in_imei(
        self,
        *,
        imei_value: str,
        product_id: int,
        location_id: int,
        order_id: int,
        user_label: str,
    ) -> None:
        imei_record = self.db.query(ProductIMEI).filter(ProductIMEI.imei == imei_value).first()
        if imei_record:
            setattr(imei_record, "product_id", product_id)
            setattr(imei_record, "location_id", location_id)
            setattr(imei_record, "vendido", False)
            setattr(imei_record, "order_id", None)
        else:
            imei_record = ProductIMEI(
                product_id=product_id,
                location_id=location_id,
                imei=imei_value,
                vendido=False,
            )
            self.db.add(imei_record)

        imei_history = IMEIHistory(
            imei=imei_value,
            product_id=product_id,
            location_id=location_id,
            event_type="retoma",
            reference_id=order_id,
            reference_type="order",
            notes=f"Ingreso por retoma en orden #{order_id}",
            created_by=user_label,
        )
        self.db.add(imei_history)

    @staticmethod
    def _build_trade_in_product_name(trade_in_item: Any) -> str:
        parts = ["RETOMA:"]
        marca = getattr(trade_in_item, "marca", None)
        modelo = getattr(trade_in_item, "modelo", None)
        if marca:
            parts.append(str(marca))
        if modelo:
            parts.append(str(modelo))
        capacidad = getattr(trade_in_item, "capacidad", None)
        if capacidad:
            parts.append(str(capacidad))
        color = getattr(trade_in_item, "color", None)
        if color:
            parts.append(f"({color})")
        return " ".join(token for token in parts if token)

    @staticmethod
    def _safe_decimal(value: Any) -> Decimal:
        try:
            if value is None:
                return Decimal("0.00")
            return Decimal(str(value))
        except Exception:  # noqa: BLE001
            return Decimal("0.00")

    @staticmethod
    def _resolve_unit_price(product_price: Any, custom_price: Optional[Any]) -> Decimal:
        base_price = Decimal(str(product_price)) if product_price is not None else Decimal("0.00")
        if custom_price is None:
            return base_price

        precio_unitario = Decimal(str(custom_price))
        if precio_unitario < 0:
            raise HTTPException(status_code=400, detail="El precio unitario no puede ser negativo")
        return precio_unitario
