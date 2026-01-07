"""
Módulo centralizado para gestión de stock e IMEIs.

Este módulo encapsula la lógica compleja de validación y modificación de stock
para evitar duplicación de código y garantizar consistencia en todas las operaciones.

Características:
- Validación atómica de stock con bloqueo de fila (SELECT ... FOR UPDATE)
- Manejo consistente de IMEIs para productos serializados
- Prevención de condiciones de carrera en operaciones concurrentes
- Logging detallado de todas las operaciones de stock
"""

from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import HTTPException
from decimal import Decimal
from datetime import UTC, datetime
import logging

from app.models import Product, Stock, Location, ProductIMEI, StockHistory, IMEIHistory

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return timezone-aware UTC timestamps for stock audits."""
    return datetime.now(UTC)


class StockValidationError(Exception):
    """Excepción personalizada para errores de validación de stock"""
    pass


class StockManager:
    """
    Gestor centralizado de operaciones de stock.
    
    Proporciona métodos transaccionales para validar y modificar stock,
    garantizando consistencia y previniendo condiciones de carrera.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def _assert_stock_invariants(self, stock: Stock, *, context: str) -> None:
        """Verifica invariantes críticas del stock.

        Invariantes:
        - cantidad_disponible >= 0
        - cantidad_reservada >= 0
        - cantidad_defectuosa >= 0
        - cantidad_reservada <= cantidad_disponible

        Si alguna falla, se trata como inconsistencia de datos.
        """
        if stock.cantidad_disponible < 0:
            raise StockValidationError(
                f"Inconsistencia de stock ({context}): cantidad_disponible < 0 ({stock.cantidad_disponible})"
            )
        if stock.cantidad_reservada < 0:
            raise StockValidationError(
                f"Inconsistencia de stock ({context}): cantidad_reservada < 0 ({stock.cantidad_reservada})"
            )
        if getattr(stock, "cantidad_defectuosa", 0) < 0:
            raise StockValidationError(
                f"Inconsistencia de stock ({context}): cantidad_defectuosa < 0 ({stock.cantidad_defectuosa})"
            )
        if stock.cantidad_reservada > stock.cantidad_disponible:
            raise StockValidationError(
                f"Inconsistencia de stock ({context}): reservado ({stock.cantidad_reservada}) "
                f"> disponible ({stock.cantidad_disponible})"
            )
    
    def validate_and_lock_stock(
        self,
        product_id: int,
        location_id: int,
        quantity: int,
        imeis_requested: Optional[List[str]] = None,
        allow_pending_imei: bool = False,
        operation_type: str = "sale"
    ) -> Tuple[Product, Stock, List[ProductIMEI]]:
        """
        Valida y bloquea stock para una operación (venta, transferencia, etc.).
        
        Esta función implementa bloqueo pesimista (SELECT ... FOR UPDATE) para
        prevenir condiciones de carrera en operaciones concurrentes.
        
        Args:
            product_id: ID del producto
            location_id: ID de la ubicación
            quantity: Cantidad solicitada
            imeis_requested: Lista de IMEIs (si producto es serializado)
            allow_pending_imei: Permitir órdenes sin IMEIs asignados
            operation_type: Tipo de operación para logging ("sale", "transfer", etc.)
        
        Returns:
            Tupla (Product, Stock, List[ProductIMEI])
        
        Raises:
            HTTPException: Si la validación falla (producto no existe, stock insuficiente, etc.)
        """
        logger.info(
            f"Validando stock - Product: {product_id}, Location: {location_id}, "
            f"Qty: {quantity}, Operation: {operation_type}"
        )
        
        # 1. Validar que la cantidad sea positiva
        if quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="La cantidad debe ser mayor a 0"
            )
        
        # 2. Validar Producto con bloqueo
        product = self.db.query(Product).filter(
            Product.id == product_id,
            Product.activo == True
        ).with_for_update().first()
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"El producto con ID {product_id} no fue encontrado o está inactivo"
            )
        
        # 3. Obtener Stock con LOCK (previene race conditions)
        stock = self.db.query(Stock).filter(
            Stock.product_id == product_id,
            Stock.location_id == location_id
        ).with_for_update().first()
        
        if not stock:
            loc_name = self._get_location_name(location_id)
            raise HTTPException(
                status_code=400,
                detail=f"El producto '{product.nombre}' (SKU: {product.sku}) no tiene stock en {loc_name}"
            )

        # 3.1 Verificar consistencia básica del registro de stock
        try:
            self._assert_stock_invariants(stock, context=f"validate_and_lock_stock:{operation_type}")
        except StockValidationError as e:
            # 409: conflicto / inconsistencia de estado
            raise HTTPException(status_code=409, detail=str(e))
        
        # 4. Validar Cantidad Disponible (considerando reservas)
        stock_libre = stock.cantidad_disponible - stock.cantidad_reservada
        
        if stock_libre < quantity:
            loc_name = self._get_location_name(location_id)
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Stock insuficiente para '{product.nombre}' (SKU: {product.sku}) en {loc_name}. "
                    f"Stock libre: {stock_libre} "
                    f"(Disponible: {stock.cantidad_disponible}, Reservado: {stock.cantidad_reservada}), "
                    f"Cantidad solicitada: {quantity}"
                )
            )
        
        # 5. Validar IMEIs (si es producto serializado)
        imeis_found = self._validate_imeis(
            product=product,
            product_id=product_id,
            location_id=location_id,
            quantity=quantity,
            imeis_requested=imeis_requested,
            allow_pending_imei=allow_pending_imei
        )
        
        logger.info(
            f"Stock validado exitosamente - Product: {product.nombre}, "
            f"Stock libre: {stock_libre}, IMEIs: {len(imeis_found)}"
        )
        
        return product, stock, imeis_found
    
    def _validate_imeis(
        self,
        product: Product,
        product_id: int,
        location_id: int,
        quantity: int,
        imeis_requested: Optional[List[str]],
        allow_pending_imei: bool
    ) -> List[ProductIMEI]:
        """
        Valida IMEIs para productos serializados.
        
        Args:
            product: Instancia del producto
            product_id: ID del producto
            location_id: ID de la ubicación
            quantity: Cantidad solicitada
            imeis_requested: Lista de IMEIs solicitados
            allow_pending_imei: Permitir operación sin IMEIs
        
        Returns:
            Lista de instancias ProductIMEI validadas y bloqueadas
        
        Raises:
            HTTPException: Si la validación de IMEIs falla
        """
        if not product.is_serialized:
            return []
        
        # Producto serializado requiere IMEIs
        if not imeis_requested:
            if allow_pending_imei:
                logger.warning(
                    f"Permitiendo operación sin IMEIs para producto serializado: {product.nombre}"
                )
                return []
            
            raise HTTPException(
                status_code=400,
                detail=(
                    f"El producto '{product.nombre}' (SKU: {product.sku}) es serializado. "
                    f"Debe proporcionar los códigos IMEI correspondientes."
                )
            )
        
        # Validar que la cantidad de IMEIs coincida con la cantidad solicitada
        if len(imeis_requested) != quantity:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cantidad de IMEIs ({len(imeis_requested)}) no coincide con "
                    f"cantidad solicitada ({quantity}) para '{product.nombre}'"
                )
            )
        
        # Buscar y validar IMEIs con bloqueo
        imeis_found = self.db.query(ProductIMEI).filter(
            ProductIMEI.product_id == product_id,
            ProductIMEI.location_id == location_id,
            ProductIMEI.vendido == False,
            ProductIMEI.imei.in_(imeis_requested)
        ).with_for_update().all()
        
        if len(imeis_found) != len(imeis_requested):
            found_set = {i.imei for i in imeis_found}
            missing = set(imeis_requested) - found_set
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Los siguientes IMEIs no están disponibles o ya fueron vendidos "
                    f"en esta ubicación: {', '.join(sorted(missing))}"
                )
            )
        
        return imeis_found
    
    def decrease_stock(
        self,
        stock: Stock,
        quantity: int,
        operation_type: str,
        notes: Optional[str] = None,
        user_id: Optional[str] = None,
        order_id: Optional[int] = None
    ) -> StockHistory:
        """
        Decrementa stock y registra en historial.
        
        IMPORTANTE: Esta función asume que el stock ya fue validado y bloqueado
        con validate_and_lock_stock().
        
        Args:
            stock: Instancia de Stock (ya bloqueada)
            quantity: Cantidad a decrementar
            operation_type: Tipo de operación ("sale", "transfer_out", "adjustment")
            notes: Notas opcionales
            user_id: ID o nombre del usuario que realiza la operación
            order_id: ID de la orden relacionada (si aplica)
        
        Returns:
            Entrada de StockHistory creada
        
        Raises:
            StockValidationError: Si el stock resultante sería inválido
        """
        if quantity <= 0:
            raise StockValidationError("La cantidad debe ser mayor a 0")

        # Validación crítica: prevenir stock por debajo de reservado
        self.db.flush()
        self.db.refresh(stock)

        stock_resultante = stock.cantidad_disponible - quantity

        if stock_resultante < 0:
            raise StockValidationError(
                f"Stock insuficiente: la operación dejaría stock negativo ({stock_resultante})."
            )
        
        if stock_resultante < stock.cantidad_reservada:
            raise StockValidationError(
                f"CRÍTICO: La operación dejaría stock ({stock_resultante}) "
                f"por debajo del stock reservado ({stock.cantidad_reservada}). "
                f"Esto no debería ocurrir si las validaciones previas fueron correctas."
            )
        
        stock_anterior = stock.cantidad_disponible
        stock_reservado = stock.cantidad_reservada

        stock_libre = stock_anterior - stock_reservado
        if stock_libre < quantity:
            raise StockValidationError(
                f"Stock insuficiente: libre={stock_libre}, solicitado={quantity}."
            )

        update_stmt = text(
            """
            UPDATE stock
            SET cantidad_disponible = cantidad_disponible - :qty
            WHERE id = :stock_id AND cantidad_disponible = :expected
            """
        )
        result = self.db.execute(
            update_stmt,
            {"qty": quantity, "stock_id": stock.id, "expected": stock_anterior},
        )

        if result.rowcount != 1:
            raise StockValidationError(
                "El stock cambió durante la operación o no hay cantidad suficiente. Intente nuevamente."
            )

        self.db.refresh(stock)

        # Safety net: re-validar invariantes
        self._assert_stock_invariants(stock, context=f"decrease_stock:{operation_type}")
        
        logger.info(
            f"Stock decrementado - Product: {stock.product_id}, Location: {stock.location_id}, "
            f"Anterior: {stock_anterior}, Nuevo: {stock.cantidad_disponible}, "
            f"Operation: {operation_type}"
        )
        
        # Registrar en historial
        history_entry = StockHistory(
            product_id=stock.product_id,
            location_id=stock.location_id,
            tipo_cambio=operation_type,
            cantidad=-quantity, # Negativo para salida
            stock_anterior=stock_anterior,
            stock_nuevo=stock.cantidad_disponible,
            referencia_id=order_id,
            referencia_tipo="order" if order_id else None,
            notas=notes or f"Operación: {operation_type}",
            usuario=user_id,
            created_at=_utcnow()
        )
        
        self.db.add(history_entry)
        return history_entry
    
    def increase_stock(
        self,
        product_id: int,
        location_id: int,
        quantity: int,
        operation_type: str,
        notes: Optional[str] = None,
        user_id: Optional[str] = None,
        create_if_missing: bool = False
    ) -> Tuple[Stock, StockHistory]:
        """
        Incrementa stock y registra en historial.
        
        Args:
            product_id: ID del producto
            location_id: ID de la ubicación
            quantity: Cantidad a incrementar
            operation_type: Tipo de operación ("transfer_in", "return", "adjustment")
            notes: Notas opcionales
            user_id: ID o nombre del usuario que realiza la operación
            create_if_missing: Crear entrada de stock si no existe
        
        Returns:
            Tupla (Stock, StockHistory)
        
        Raises:
            HTTPException: Si el stock no existe y create_if_missing=False
        """
        if quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="La cantidad debe ser mayor a 0"
            )
        
        # Buscar o crear stock con bloqueo
        stock = self.db.query(Stock).filter(
            Stock.product_id == product_id,
            Stock.location_id == location_id
        ).with_for_update().first()
        
        if not stock:
            if not create_if_missing:
                loc_name = self._get_location_name(location_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"No existe registro de stock para este producto en {loc_name}"
                )
            
            # Crear nuevo registro de stock
            stock = Stock(
                product_id=product_id,
                location_id=location_id,
                cantidad_disponible=0,
                cantidad_reservada=0
            )
            self.db.add(stock)
            self.db.flush()  # Obtener ID antes de continuar
        
        # Incrementar stock
        stock_anterior = stock.cantidad_disponible
        stock.cantidad_disponible += quantity

        # Safety net: re-validar invariantes
        self._assert_stock_invariants(stock, context=f"increase_stock:{operation_type}")
        
        logger.info(
            f"Stock incrementado - Product: {product_id}, Location: {location_id}, "
            f"Anterior: {stock_anterior}, Nuevo: {stock.cantidad_disponible}, "
            f"Operation: {operation_type}"
        )
        
        # Registrar en historial
        history_entry = StockHistory(
            product_id=product_id,
            location_id=location_id,
            tipo_cambio=operation_type,
            cantidad=quantity,
            stock_anterior=stock_anterior,
            stock_nuevo=stock.cantidad_disponible,
            notas=notes or f"Operación: {operation_type}",
            usuario=user_id,
            created_at=_utcnow()
        )
        
        self.db.add(history_entry)
        return stock, history_entry

    def process_return_stock(
        self,
        *,
        product_id: int,
        location_id: int,
        quantity: int,
        defective: bool,
        reference_id: int,
        notes: Optional[str] = None,
        user_id: Optional[str] = None,
        create_if_missing: bool = True,
    ) -> Tuple[Stock, StockHistory]:
        """Gestiona el reintegro de stock por una devolución (defectuoso o vendible)."""
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0")

        stock = (
            self.db.query(Stock)
            .filter(Stock.product_id == product_id, Stock.location_id == location_id)
            .with_for_update()
            .first()
        )

        if not stock:
            if not create_if_missing:
                raise HTTPException(status_code=404, detail="Stock no encontrado para devolución")
            stock = Stock(
                product_id=product_id,
                location_id=location_id,
                cantidad_disponible=0,
                cantidad_reservada=0,
                cantidad_defectuosa=0,
            )
            self.db.add(stock)
            self.db.flush()

        if getattr(stock, "cantidad_defectuosa", None) is None:
            stock.cantidad_defectuosa = 0

        stock_anterior = stock.cantidad_disponible

        if defective:
            stock.cantidad_defectuosa = (stock.cantidad_defectuosa or 0) + quantity
        else:
            stock.cantidad_disponible += quantity

        self._assert_stock_invariants(stock, context="process_return_stock")

        history_entry = StockHistory(
            product_id=product_id,
            location_id=location_id,
            tipo_cambio="devolucion_defectuosa" if defective else "devolucion",
            cantidad=quantity,
            stock_anterior=stock_anterior,
            stock_nuevo=stock.cantidad_disponible,
            referencia_id=reference_id,
            referencia_tipo="return",
            notas=notes or "Reingreso por devolución",
            usuario=user_id,
            created_at=_utcnow(),
        )

        self.db.add(history_entry)
        return stock, history_entry

    def process_return_imeis(
        self,
        imeis: List[ProductIMEI],
        *,
        return_id: int,
        condition: str,
        action: str,
        user_id: Optional[str] = None,
    ) -> List[IMEIHistory]:
        """Libera IMEIs vendidos registrando el historial como devolución."""
        history_entries: List[IMEIHistory] = []

        for imei_record in imeis:
            imei_record.vendido = False
            imei_record.fecha_venta = None
            imei_record.order_id = None

            history_entry = IMEIHistory(
                imei=imei_record.imei,
                product_id=imei_record.product_id,
                location_id=imei_record.location_id,
                event_type="devolucion",
                reference_id=return_id,
                reference_type="return",
                notes=f"Devolución por {condition} - Acción: {action}",
                created_by=user_id,
                created_at=_utcnow(),
            )

            self.db.add(history_entry)
            history_entries.append(history_entry)

        return history_entries
    
    def mark_imeis_as_sold(
        self,
        imeis: List[ProductIMEI],
        order_id: int,
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[IMEIHistory]:
        """
        Marca IMEIs como vendidos y registra en historial.
        
        Args:
            imeis: Lista de instancias ProductIMEI (ya bloqueadas)
            order_id: ID de la orden de venta
            notes: Notas opcionales
            user_id: ID o nombre del usuario que realiza la operación
        
        Returns:
            Lista de entradas de IMEIHistory creadas
        """
        history_entries = []
        
        for imei_record in imeis:
            imei_record.vendido = True
            imei_record.fecha_venta = _utcnow()
            imei_record.order_id = order_id
            
            # Registrar en historial
            history_entry = IMEIHistory(
                imei=imei_record.imei,
                product_id=imei_record.product_id,
                location_id=imei_record.location_id,
                event_type="venta",
                reference_id=order_id,
                reference_type="order",
                notes=notes or f"Vendido en orden #{order_id}",
                created_by=user_id,
                created_at=_utcnow()
            )
            
            self.db.add(history_entry)
            history_entries.append(history_entry)
            
            logger.info(
                f"IMEI marcado como vendido - IMEI: {imei_record.imei}, "
                f"Product: {imei_record.product_id}, Order: {order_id}"
            )
        
        return history_entries
    
    def transfer_imeis(
        self,
        imeis: List[ProductIMEI],
        to_location_id: int,
        transfer_id: int,
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[IMEIHistory]:
        """
        Transfiere IMEIs a otra ubicación y registra en historial.
        
        Args:
            imeis: Lista de instancias ProductIMEI (ya bloqueadas)
            to_location_id: ID de la ubicación destino
            transfer_id: ID de la transferencia
            notes: Notas opcionales
            user_id: ID o nombre del usuario que realiza la operación
        
        Returns:
            Lista de entradas de IMEIHistory creadas
        """
        history_entries = []
        
        for imei_record in imeis:
            from_location_id = imei_record.location_id
            imei_record.location_id = to_location_id
            
            # Registrar en historial
            history_entry = IMEIHistory(
                imei=imei_record.imei,
                product_id=imei_record.product_id,
                location_id=to_location_id, # Nueva ubicación
                event_type="transferencia",
                reference_id=transfer_id,
                reference_type="transfer",
                notes=notes or f"Transferido de {from_location_id} a {to_location_id}",
                created_by=user_id,
                created_at=_utcnow()
            )
            
            self.db.add(history_entry)
            history_entries.append(history_entry)
            
            logger.info(
                f"IMEI transferido - IMEI: {imei_record.imei}, "
                f"From: {from_location_id}, To: {to_location_id}, Transfer: {transfer_id}"
            )
        
        return history_entries
    
    def release_imeis(
        self,
        imeis: List[ProductIMEI],
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[IMEIHistory]:
        """
        Libera IMEIs (marca como no vendidos) y registra en historial.
        
        Args:
            imeis: Lista de instancias ProductIMEI (ya bloqueadas)
            notes: Notas opcionales
            user_id: ID o nombre del usuario que realiza la operación
        
        Returns:
            Lista de entradas de IMEIHistory creadas
        """
        history_entries = []
        
        for imei_record in imeis:
            imei_record.vendido = False
            imei_record.fecha_venta = None
            imei_record.order_id = None
            
            # Registrar en historial
            history_entry = IMEIHistory(
                imei=imei_record.imei,
                product_id=imei_record.product_id,
                location_id=imei_record.location_id,
                event_type="liberacion",
                reference_id=None,
                reference_type="manual_release",
                notes=notes or "Liberado manualmente o por cancelación",
                created_by=user_id,
                created_at=_utcnow()
            )
            
            self.db.add(history_entry)
            history_entries.append(history_entry)
            
            logger.info(
                f"IMEI liberado - IMEI: {imei_record.imei}, "
                f"Product: {imei_record.product_id}"
            )
        
        return history_entries

    def reserve_stock(
        self,
        stock: Stock,
        quantity: int,
        transfer_id: int,
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> StockHistory:
        """
        Reserva stock para una transferencia.
        
        Args:
            stock: Instancia de Stock (ya bloqueada)
            quantity: Cantidad a reservar
            transfer_id: ID de la transferencia
            notes: Notas opcionales
            user_id: ID o nombre del usuario
            
        Returns:
            Entrada de StockHistory
        """
        if quantity <= 0:
            raise StockValidationError("La cantidad debe ser mayor a 0")

        # Refrescar desde la base para evitar reservar sobre snapshots obsoletos
        self.db.refresh(stock)

        self._assert_stock_invariants(stock, context="reserve_stock:pre")

        # Validar que hay suficiente stock libre con los datos más recientes
        stock_libre = stock.cantidad_disponible - stock.cantidad_reservada
        if stock_libre < quantity:
            raise StockValidationError(
                f"Stock insuficiente para reservar. Libre: {stock_libre}, Solicitado: {quantity}"
            )

        stock_anterior_libre = stock_libre

        rows_updated = (
            self.db.query(Stock)
            .filter(
                Stock.id == stock.id,
                Stock.cantidad_disponible == stock.cantidad_disponible,
                Stock.cantidad_reservada == stock.cantidad_reservada,
            )
            .update(
                {Stock.cantidad_reservada: Stock.cantidad_reservada + quantity},
                synchronize_session=False,
            )
        )

        if rows_updated != 1:
            raise StockValidationError(
                "El stock cambió mientras se intentaba reservar. Intente de nuevo."
            )

        self.db.flush()
        self.db.refresh(stock)
        stock_nuevo_libre = stock.cantidad_disponible - stock.cantidad_reservada

        self._assert_stock_invariants(stock, context="reserve_stock:post")
        
        history_entry = StockHistory(
            product_id=stock.product_id,
            location_id=stock.location_id,
            tipo_cambio='transferencia_reserva',
            cantidad=-quantity, # Negativo porque reduce stock libre
            stock_anterior=stock_anterior_libre,
            stock_nuevo=stock_nuevo_libre,
            referencia_id=transfer_id,
            referencia_tipo='transfer_pending',
            notas=notes or f"Reserva para transferencia #{transfer_id}",
            usuario=user_id,
            created_at=_utcnow()
        )
        
        self.db.add(history_entry)
        return history_entry

    def release_reservation(
        self,
        stock: Stock,
        quantity: int,
        transfer_id: int,
        notes: Optional[str] = None,
        user_id: Optional[str] = None,
        is_rejection: bool = False
    ) -> Optional[StockHistory]:
        """
        Libera stock reservado (por rechazo o cancelación).
        
        Args:
            stock: Instancia de Stock (ya bloqueada)
            quantity: Cantidad a liberar
            transfer_id: ID de la transferencia
            notes: Notas opcionales
            user_id: ID o nombre del usuario
            is_rejection: True si es rechazo/cancelación (aumenta stock libre), False si es confirmación (no cambia stock libre, solo reduce reserva)
            
        Returns:
            Entrada de StockHistory (solo si es rechazo/cancelación)
        """
        if quantity <= 0:
            raise StockValidationError("La cantidad debe ser mayor a 0")

        self._assert_stock_invariants(stock, context="release_reservation:pre")

        if stock.cantidad_reservada < quantity:
            # Tratar como inconsistencia: mejor fallar que ocultar un bug.
            raise StockValidationError(
                f"Inconsistencia de reserva: reservado ({stock.cantidad_reservada}) < liberar ({quantity})"
            )
            
        stock_anterior_libre = stock.cantidad_disponible - stock.cantidad_reservada
        stock.cantidad_reservada = stock.cantidad_reservada - quantity
        stock_nuevo_libre = stock.cantidad_disponible - stock.cantidad_reservada

        self._assert_stock_invariants(stock, context="release_reservation:post")
        
        if is_rejection:
            history_entry = StockHistory(
                product_id=stock.product_id,
                location_id=stock.location_id,
                tipo_cambio='transferencia_rechazada',
                cantidad=quantity, # Positivo porque aumenta stock libre
                stock_anterior=stock_anterior_libre,
                stock_nuevo=stock_nuevo_libre,
                referencia_id=transfer_id,
                referencia_tipo='transfer_rejected',
                notas=notes or f"Reserva liberada de transferencia #{transfer_id}",
                usuario=user_id,
                created_at=_utcnow()
            )
            self.db.add(history_entry)
            return history_entry
        
        return None

    def reserve_imeis(
        self,
        imeis: List[ProductIMEI],
        transfer_id: int
    ):
        """Asigna transfer_id a los IMEIs"""
        for imei in imeis:
            imei.transfer_id = transfer_id

    def release_reserved_imeis(
        self,
        imeis: List[ProductIMEI]
    ):
        """Libera transfer_id de los IMEIs"""
        for imei in imeis:
            imei.transfer_id = None

    def _get_location_name(self, location_id: int) -> str:
        """Obtiene el nombre de una ubicación (con fallback)"""
        location = self.db.query(Location).filter(Location.id == location_id).first()
        return location.nombre if location else f"Ubicación #{location_id}"


# Funciones helper para compatibilidad con código existente
def get_stock_manager(db: Session) -> StockManager:
    """Factory function para obtener instancia de StockManager"""
    return StockManager(db)
