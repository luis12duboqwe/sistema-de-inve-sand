from pathlib import Path

path = Path("backend/app/routers/multistore_control.py")
text = path.read_text()
old = '''    total_cost = Decimal("0")
    try:
        for item in payload.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no encontrado")
            imeis = item.imeis or []
'''
new = '''    total_cost = Decimal("0")
    try:
        # Keep one global lock order for workflows that mutate Product + Stock.
        # Lock every referenced product first and do it in deterministic ID order
        # before any Stock row is locked or created. Besides matching manual
        # restock (Product -> Stock), this prevents two receipts with reversed
        # payload item order from forming a Product-lock cycle.
        products_by_id: dict[int, Product] = {}
        for product_id in sorted({item.product_id for item in payload.items}):
            product = (
                db.query(Product)
                .filter(Product.id == product_id)
                .with_for_update()
                .first()
            )
            if not product:
                raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado")
            products_by_id[product_id] = product

        for item in payload.items:
            product = products_by_id[item.product_id]
            imeis = item.imeis or []
'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"expected exactly one purchase-receipt lock-order target, found {count}")
path.write_text(text.replace(old, new, 1))
