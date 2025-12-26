# Guía de Refactorización y Mejora Continua

## Introducción

Este documento proporciona una guía estructurada para refactorizar y mejorar el sistema de forma incremental, priorizando cambios que maximicen la calidad sin comprometer la funcionalidad existente.

---

## 1. Refactorización de Gestión de Stock

### Problema Identificado
La lógica de validación y modificación de stock está duplicada en múltiples archivos:
- `backend/app/routers/orders.py` - Función `_get_and_validate_stock()`
- `backend/app/routers/stock_transfers.py` - Validaciones similares
- Riesgo de inconsistencias y bugs difíciles de rastrear

### Solución Implementada
✅ Módulo centralizado: `backend/app/utils/stock_manager.py`

**Clase `StockManager`** con métodos:
- `validate_and_lock_stock()` - Validación atómica con bloqueo
- `decrease_stock()` - Decremento seguro con historial
- `increase_stock()` - Incremento seguro con historial
- `mark_imeis_as_sold()` - Gestión de IMEIs vendidos
- `transfer_imeis()` - Transferencia de IMEIs entre ubicaciones

### Migración Recomendada

#### Paso 1: Actualizar `orders.py`

**Antes:**
```python
def _get_and_validate_stock(db, product_id, location_id, quantity, imeis_requested, allow_pending_imei=False):
    # ... 80 líneas de código ...
```

**Después:**
```python
from app.utils.stock_manager import get_stock_manager

def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    stock_manager = get_stock_manager(db)
    
    for item in order.items:
        product, stock, imeis = stock_manager.validate_and_lock_stock(
            product_id=item.product_id,
            location_id=order.source_location_id,
            quantity=item.cantidad,
            imeis_requested=item.imeis,
            allow_pending_imei=order.allow_pending_imei,
            operation_type="sale"
        )
        
        # Decrementar stock
        stock_manager.decrease_stock(
            stock=stock,
            quantity=item.cantidad,
            operation_type="sale",
            notes=f"Venta en orden #{order.id}",
            order_id=order.id
        )
        
        # Marcar IMEIs como vendidos
        if imeis:
            stock_manager.mark_imeis_as_sold(
                imeis=imeis,
                order_id=order.id
            )
```

#### Paso 2: Actualizar `stock_transfers.py`

Similar al paso anterior, reemplazar lógica duplicada con llamadas a `StockManager`.

#### Beneficios:
- ✅ Código más limpio y mantenible
- ✅ Validaciones consistentes en todo el sistema
- ✅ Logging centralizado de operaciones de stock
- ✅ Fácil agregar nuevas validaciones (aplica a todas las operaciones)
- ✅ Tests unitarios más simples (probar `StockManager` aisladamente)

---

## 2. Refactorización de Creación de Órdenes

### Problema Identificado
La función `create_order()` en `orders.py` tiene >400 líneas y maneja:
- Validación de perfiles (V1/V2)
- Validación de stock item por item
- Cálculo de totales y descuentos
- Manejo de trade-ins
- Verificación de financiamiento
- Registro de historial
- Manejo de IMEIs

### Solución Propuesta
Dividir en funciones más pequeñas con responsabilidades únicas.

#### Estructura Refactorizada

```python
# backend/app/services/order_service.py (NUEVO ARCHIVO)

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models import Order, OrderItem, SalesProfile, Location, TradeIn
from app.schemas import OrderCreate, OrderItemCreate
from app.utils.stock_manager import StockManager
from app.utils.validators import InputValidator


class OrderService:
    """
    Servicio para gestión de órdenes.
    Encapsula lógica de negocio compleja.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.stock_manager = StockManager(db)
    
    def validate_sales_profile(self, order_data: OrderCreate) -> Tuple[Optional[SalesProfile], Optional[Profile]]:
        """
        Valida y obtiene perfil de venta (V2.0) o perfil legacy (V1.0).
        
        Returns:
            Tuple (SalesProfile | None, Profile | None)
        """
        # ... lógica de validación ...
    
    def validate_location(self, location_id: int) -> Location:
        """
        Valida que la ubicación existe y está activa.
        """
        # ... lógica de validación ...
    
    def validate_and_reserve_items(
        self,
        items: List[OrderItemCreate],
        location_id: int
    ) -> List[Tuple[Product, Stock, List[ProductIMEI]]]:
        """
        Valida stock e IMEIs para todos los items de la orden.
        Retorna información necesaria para crear la orden.
        """
        validated_items = []
        
        for item in items:
            product, stock, imeis = self.stock_manager.validate_and_lock_stock(
                product_id=item.product_id,
                location_id=location_id,
                quantity=item.cantidad,
                imeis_requested=item.imeis,
                operation_type="sale"
            )
            validated_items.append((product, stock, imeis))
        
        return validated_items
    
    def calculate_totals(
        self,
        items: List[OrderItemCreate],
        validated_products: List[Product],
        discount_rate: Optional[Decimal] = None,
        trade_in_value: Optional[Decimal] = None
    ) -> dict:
        """
        Calcula subtotal, descuentos y total de la orden.
        
        Returns:
            Dict con: subtotal, discount_amount, trade_in_applied, total
        """
        subtotal = Decimal(0)
        
        for item, product in zip(items, validated_products):
            if item.es_regalo_promocion:
                continue  # Regalos no cuentan en total
            
            subtotal += Decimal(str(item.precio_unitario)) * item.cantidad
        
        discount_amount = Decimal(0)
        if discount_rate:
            discount_amount = subtotal * (discount_rate / 100)
        
        trade_in_applied = Decimal(0)
        if trade_in_value:
            trade_in_applied = min(trade_in_value, subtotal - discount_amount)
        
        total = subtotal - discount_amount - trade_in_applied
        
        return {
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "trade_in_applied": trade_in_applied,
            "total": max(total, Decimal(0))  # Nunca negativo
        }
    
    def process_trade_ins(
        self,
        order_id: int,
        trade_ins_data: Optional[List[dict]]
    ) -> List[TradeIn]:
        """
        Procesa trade-ins asociados a la orden.
        """
        # ... lógica de trade-ins ...
    
    def create_order_with_items(
        self,
        order_data: OrderCreate,
        validated_items: List[Tuple[Product, Stock, List[ProductIMEI]]],
        totals: dict,
        sales_profile_id: int,
        location_id: int
    ) -> Order:
        """
        Crea la orden y sus items en la base de datos.
        Decrementa stock y marca IMEIs como vendidos.
        """
        # Crear orden
        order = Order(
            sales_profile_id=sales_profile_id,
            source_location_id=location_id,
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            customer_email=order_data.customer_email,
            canal=order_data.canal,
            metodo_pago=order_data.metodo_pago,
            subtotal=totals["subtotal"],
            descuento=totals["discount_amount"],
            total=totals["total"],
            estado="pendiente"
        )
        
        self.db.add(order)
        self.db.flush()  # Obtener order.id
        
        # Crear items y decrementar stock
        for item_data, (product, stock, imeis) in zip(order_data.items, validated_items):
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                cantidad=item_data.cantidad,
                precio_unitario=item_data.precio_unitario,
                es_regalo_promocion=item_data.es_regalo_promocion or False
            )
            self.db.add(order_item)
            
            # Decrementar stock
            self.stock_manager.decrease_stock(
                stock=stock,
                quantity=item_data.cantidad,
                operation_type="sale",
                notes=f"Venta en orden #{order.id}",
                order_id=order.id
            )
            
            # Marcar IMEIs como vendidos
            if imeis:
                self.stock_manager.mark_imeis_as_sold(
                    imeis=imeis,
                    order_id=order.id,
                    notes=f"Vendido en orden #{order.id}"
                )
        
        return order
    
    def create_order(self, order_data: OrderCreate, user_id: Optional[int] = None) -> Order:
        """
        Crea una orden completa (función principal).
        
        Este método orquesta todas las validaciones y operaciones necesarias.
        """
        try:
            # 1. Validar perfil de venta
            sales_profile, _ = self.validate_sales_profile(order_data)
            
            # 2. Validar ubicación
            location = self.validate_location(order_data.source_location_id)
            
            # 3. Validar items y stock
            validated_items = self.validate_and_reserve_items(
                order_data.items,
                order_data.source_location_id
            )
            
            # 4. Calcular totales
            products = [item[0] for item in validated_items]
            totals = self.calculate_totals(
                order_data.items,
                products,
                discount_rate=order_data.discount_rate,
                trade_in_value=order_data.trade_in_value
            )
            
            # 5. Crear orden
            order = self.create_order_with_items(
                order_data,
                validated_items,
                totals,
                sales_profile.id,
                location.id
            )
            
            # 6. Procesar trade-ins (si aplica)
            if order_data.trade_ins:
                self.process_trade_ins(order.id, order_data.trade_ins)
            
            # 7. Commit transacción
            self.db.commit()
            self.db.refresh(order)
            
            return order
            
        except Exception as e:
            self.db.rollback()
            raise


# En backend/app/routers/orders.py

from app.services.order_service import OrderService

@router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Crea una nueva orden (refactorizado)."""
    order_service = OrderService(db)
    
    try:
        created_order = order_service.create_order(
            order,
            user_id=current_user.id if current_user else None
        )
        return _serialize_order(created_order)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al crear orden: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al crear orden")
```

#### Beneficios:
- ✅ Funciones pequeñas y testeables
- ✅ Responsabilidades claramente separadas
- ✅ Fácil agregar nuevas validaciones
- ✅ Logging más granular (cada función puede loggear)
- ✅ Reutilizable (OrderService puede usarse en otros contextos)

---

## 3. Mejoras en Validaciones

### Solución Implementada
✅ Módulo centralizado: `backend/app/utils/validators.py`

**Clase `InputValidator`** con métodos estáticos:
- `validate_email()` - Formato de email
- `validate_phone()` - Formato de teléfono
- `validate_text_field()` - Texto genérico con límites
- `validate_sku()` - SKU de productos
- `validate_imei()` - Código IMEI
- `validate_positive_number()` - Números positivos (precios, cantidades)
- `validate_date_range()` - Rangos de fechas
- `sanitize_html()` - Prevención de XSS

### Uso en Routers

**Antes:**
```python
@router.post("/api/products")
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    # Sin validación adicional, solo Pydantic
    new_product = Product(**product.dict())
    db.add(new_product)
    db.commit()
    return new_product
```

**Después:**
```python
from app.utils.validators import InputValidator, ValidationError

@router.post("/api/products")
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    try:
        # Validaciones adicionales
        validated_sku = InputValidator.validate_sku(product.sku)
        validated_nombre = InputValidator.validate_text_field(
            product.nombre,
            field_name="nombre",
            max_length=200
        )
        
        # Validar precio positivo
        validated_precio = InputValidator.validate_positive_number(
            product.precio,
            field_name="precio",
            allow_zero=False
        )
        
        new_product = Product(
            sku=validated_sku,
            nombre=validated_nombre,
            precio=validated_precio,
            # ... otros campos ...
        )
        
        db.add(new_product)
        db.commit()
        return new_product
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 4. Sistema de Logging Mejorado

### Solución Implementada
✅ Módulo: `backend/app/utils/logging_config.py`

**Características:**
- Logging estructurado (JSON) para producción
- Logging colorizado para desarrollo
- Rotación de archivos automática
- Niveles configurables por módulo
- Context manager para agregar contexto temporal

### Configuración en `main.py`

```python
# backend/app/main.py

from app.utils.logging_config import setup_logging, get_logger
from app.config_production import prod_settings

# Configurar logging al iniciar aplicación
@app.on_event("startup")
async def startup_event():
    # Configurar sistema de logging
    setup_logging(
        log_level=prod_settings.LOG_LEVEL,
        log_dir=prod_settings.LOG_DIR,
        enable_file_logging=prod_settings.ENABLE_FILE_LOGGING,
        structured=prod_settings.LOG_FORMAT == "json"
    )
    
    logger = get_logger(__name__)
    logger.info(f"Aplicación iniciada - Entorno: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Verificar preparación para producción
    if prod_settings.is_production():
        warnings = prod_settings.validate_production_config()
        if warnings:
            for warning in warnings:
                logger.warning(f"Configuración: {warning}")

# Usar en routers
from app.utils.logging_config import get_logger, LogContext

logger = get_logger(__name__)

@router.post("/api/orders")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    with LogContext(user_id=current_user.id, order_id=None):
        logger.info(f"Creando orden para cliente: {order.customer_name}")
        
        try:
            # ... crear orden ...
            logger.info(f"Orden #{new_order.id} creada exitosamente")
            return new_order
        except Exception as e:
            logger.error(f"Error al crear orden: {e}", exc_info=True)
            raise
```

---

## 5. Sanitización HTML para Exportación

### Solución Implementada
✅ Módulo: `backend/app/utils/html_export.py`

**Clase `SafeHTMLBuilder`** para generar HTML seguro:
- `escape()` - Escapa caracteres HTML
- `format_currency()` - Formatea moneda de forma segura
- `format_date()` - Formatea fechas
- `build_table()` - Construye tablas HTML
- `build_order_html()` - HTML completo para órdenes (PDF/impresión)
- `build_report_html()` - HTML para reportes genéricos

### Uso en Exportación de Órdenes

**Antes (INSEGURO):**
```python
def export_order_to_html(order: Order) -> str:
    # RIESGO: No escapa datos de usuario
    html = f"""
    <h1>Orden #{order.id}</h1>
    <p>Cliente: {order.customer_name}</p>
    <p>Total: {order.total}</p>
    """
    return html
```

**Después (SEGURO):**
```python
from app.utils.html_export import SafeHTMLBuilder

def export_order_to_html(order: Order) -> str:
    order_data = {
        "id": order.id,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "created_at": order.created_at,
        "total": order.total,
        "moneda": order.moneda or "HNL",
        "items": [
            {
                "product": {"nombre": item.product.nombre},
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario
            }
            for item in order.items
        ]
    }
    
    return SafeHTMLBuilder.build_order_html(order_data)
```

---

## 6. Configuración de Producción

### Archivos Creados
✅ `backend/.env.production.example` - Plantilla de configuración segura
✅ `backend/app/config_production.py` - Settings extendidos
✅ `backend/check_production_readiness.py` - Script de verificación

### Uso

```bash
# 1. Copiar plantilla de producción
cp backend/.env.production.example backend/.env

# 2. Editar valores (SECRET_KEY, DATABASE_URL, CORS, etc.)
nano backend/.env

# 3. Verificar configuración
cd backend
python check_production_readiness.py

# 4. Si todo está OK, desplegar
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 7. Plan de Migración Incremental

### Fase 1: Infraestructura (Sin cambios funcionales)
**Duración: 1-2 días**

1. ✅ Crear módulos de utilidades (ya hecho)
2. ✅ Agregar logging en puntos críticos
3. ✅ Configurar monitoreo básico (logs)
4. ✅ Probar que sistema sigue funcionando igual

### Fase 2: Refactorizar Stock (Alto impacto)
**Duración: 2-3 días**

1. Migrar `orders.py` a usar `StockManager`
2. Migrar `stock_transfers.py` a usar `StockManager`
3. Eliminar código duplicado
4. Agregar tests unitarios para `StockManager`
5. Testing exhaustivo de flujo de ventas/transferencias

### Fase 3: Refactorizar Órdenes (Mantenibilidad)
**Duración: 3-4 días**

1. Crear `OrderService` con métodos separados
2. Migrar `create_order()` a usar servicio
3. Agregar validaciones mejoradas
4. Testing de todos los casos de órdenes (con/sin trade-in, con/sin IMEIs, etc.)

### Fase 4: Seguridad y Producción (Deployment ready)
**Duración: 2-3 días**

1. Aplicar sanitización HTML en todos los exports
2. Agregar validaciones en frontend
3. Configurar .env de producción
4. Ejecutar `check_production_readiness.py`
5. Corregir todos los warnings
6. Documentar proceso de deployment

### Fase 5: Completar IA (Opcional - post v1.0)
**Duración: 1-2 semanas**

1. Integrar OpenAI API en backend
2. Crear workflow N8N para bots
3. Implementar forecasting con algoritmo mejorado
4. Testing de funcionalidades de IA

---

## 8. Tests Recomendados

### Tests Unitarios (`backend/tests/test_stock_manager.py`)

```python
import pytest
from app.utils.stock_manager import StockManager
from app.models import Product, Stock, Location

def test_validate_stock_insufficient(db_session):
    """Debe lanzar HTTPException si stock insuficiente"""
    manager = StockManager(db_session)
    
    with pytest.raises(HTTPException) as exc_info:
        manager.validate_and_lock_stock(
            product_id=1,
            location_id=1,
            quantity=100,  # Más del disponible
            imeis_requested=None
        )
    
    assert exc_info.value.status_code == 400
    assert "insuficiente" in exc_info.value.detail.lower()

def test_decrease_stock_updates_history(db_session):
    """Debe crear entrada en StockHistory al decrementar"""
    manager = StockManager(db_session)
    
    stock = db_session.query(Stock).filter_by(product_id=1, location_id=1).first()
    initial_quantity = stock.cantidad_disponible
    
    history_entry = manager.decrease_stock(
        stock=stock,
        quantity=5,
        operation_type="sale",
        notes="Test sale"
    )
    
    assert stock.cantidad_disponible == initial_quantity - 5
    assert history_entry.cantidad_cambio == -5
    assert history_entry.tipo_movimiento == "sale"

# ... más tests ...
```

### Tests de Integración (`backend/tests/test_orders_integration.py`)

```python
def test_create_order_decrements_stock(client, auth_headers):
    """Crear orden debe decrementar stock correctamente"""
    # Obtener stock inicial
    response = client.get("/api/products/1")
    initial_stock = response.json()["stock_disponible"]
    
    # Crear orden
    order_data = {
        "sales_profile_slug": "test-profile",
        "source_location_id": 1,
        "customer_name": "Test Customer",
        "customer_phone": "+50499887766",
        "items": [
            {"product_id": 1, "cantidad": 2, "precio_unitario": 100}
        ]
    }
    
    response = client.post("/api/orders", json=order_data, headers=auth_headers)
    assert response.status_code == 201
    
    # Verificar stock decrementado
    response = client.get("/api/products/1")
    new_stock = response.json()["stock_disponible"]
    assert new_stock == initial_stock - 2
```

---

## 9. Checklist de Calidad

### Antes de Cada Commit
- [ ] Código sigue convenciones del proyecto
- [ ] No hay logs de debug/print statements
- [ ] Funciones tienen docstrings
- [ ] No hay código comentado (eliminar o explicar)
- [ ] Tests pasan (`python -m pytest`)

### Antes de Cada Release
- [ ] Todas las funcionalidades prometidas están implementadas o documentadas como pendientes
- [ ] Sistema pasa `check_production_readiness.py` sin warnings críticos
- [ ] Documentación actualizada (README, ESTADO_IA.md, etc.)
- [ ] Backups de base de datos configurados
- [ ] Logs de errores se revisan regularmente
- [ ] Plan de rollback documentado

---

## 10. Recursos y Documentación

### Archivos de Referencia
- `backend/app/utils/` - Utilidades implementadas
- `docs/ESTADO_IA.md` - Estado de funcionalidades de IA
- `backend/.env.production.example` - Configuración segura
- `backend/check_production_readiness.py` - Verificación de producción

### Comandos Útiles

```bash
# Verificar preparación para producción
cd backend
python check_production_readiness.py

# Ejecutar tests
python -m pytest tests/ -v

# Ver logs en tiempo real
tail -f logs/app.log

# Backup de base de datos
cp inventory.db inventory_backup_$(date +%Y%m%d).db

# Reiniciar sistema con nuevos cambios
./stop-all.sh  # Si existe
./start-all.sh  # Si existe
```

---

## Conclusión

Esta guía proporciona una ruta clara para mejorar el sistema de forma incremental:

1. **Inmediato** (Fase 1): Infraestructura de logging y monitoreo
2. **Corto plazo** (Fases 2-3): Refactorización de código crítico
3. **Medio plazo** (Fase 4): Preparación para producción
4. **Largo plazo** (Fase 5): Completar funcionalidades avanzadas de IA

Cada fase es independiente y puede pausarse sin comprometer la funcionalidad del sistema.

**Recomendación final**: Priorizar Fases 1-4 para tener un sistema sólido y production-ready, dejar Fase 5 como mejora futura post-lanzamiento.

---

**Última actualización**: Diciembre 26, 2024
