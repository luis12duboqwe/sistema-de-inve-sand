from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session, sessionmaker

from app.models import Product
from app.routers import products
from app.schemas import ProductUpdate


def _product(db_session: Session, *, sku: str, name: str) -> Product:
    product = Product(
        sku=sku,
        nombre=name,
        categoria="accesorio",
        marca="Marca QA",
        modelo=f"Modelo-{uuid4().hex[:8]}",
        condicion="nuevo",
        precio=100,
        costo=50,
        moneda="Lps",
        garantia_meses=0,
        activo=True,
        is_serialized=False,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def test_concurrent_product_updates_report_duplicate_sku_instead_of_500(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    first = _product(db_session, sku=f"SKU-A-{suffix}", name=f"Producto A {suffix}")
    second = _product(db_session, sku=f"SKU-B-{suffix}", name=f"Producto B {suffix}")
    first_id = int(first.id)
    second_id = int(second.id)
    target_sku = f"SKU-RACE-{suffix}"

    bind = db_session.get_bind()
    barrier = Barrier(2)

    class BarrierSession(Session):
        def commit(self):
            barrier.wait(timeout=10)
            return super().commit()

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=bind,
        class_=BarrierSession,
    )

    def update(product_id: int):
        session = SessionLocal()
        try:
            try:
                updated = products.update_product(
                    product_id,
                    ProductUpdate(sku=target_sku),
                    session,
                )
                return (200, updated.sku)
            except HTTPException as exc:
                return (exc.status_code, str(exc.detail))
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, (first_id, second_id)))

    assert sorted(status for status, _ in results) == [200, 400]
    assert any(
        target_sku in detail and "SKU" in detail
        for status, detail in results
        if status == 400
    )

    db_session.expire_all()
    assert db_session.query(Product).filter(Product.sku == target_sku).count() == 1
    assert db_session.query(Product).filter(Product.id.in_([first_id, second_id])).count() == 2
