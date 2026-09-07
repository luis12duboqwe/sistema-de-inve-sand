from pathlib import Path

# Production: use PostgreSQL FOR NO KEY UPDATE for Product serialization.
products_path = Path("backend/app/routers/products.py")
text = products_path.read_text()
old = '''    # Serialize restocks for the same product before reading stock or cost.\n    # This protects both existing-stock increments and the first Stock-row create.\n    product = (\n        db.query(Product)\n        .filter(Product.id == product_id)\n        .with_for_update()\n        .first()\n    )\n'''
new = '''    # Serialize restocks for the same product before reading stock or cost.\n    # PostgreSQL FOR NO KEY UPDATE still conflicts with other restock/cost\n    # writers, while remaining compatible with FK KEY SHARE checks emitted by\n    # stock-history writers that may already hold the Stock row.\n    product = (\n        db.query(Product)\n        .filter(Product.id == product_id)\n        .with_for_update(key_share=True)\n        .first()\n    )\n'''
if text.count(old) != 1:
    raise SystemExit(f"expected one restock Product lock block, found {text.count(old)}")
products_path.write_text(text.replace(old, new, 1))

multi_path = Path("backend/app/routers/multistore_control.py")
text = multi_path.read_text()
old = '''            product = (\n                db.query(Product)\n                .filter(Product.id == product_id)\n                .with_for_update()\n                .first()\n            )\n'''
new = '''            product = (\n                db.query(Product)\n                .filter(Product.id == product_id)\n                .with_for_update(key_share=True)\n                .first()\n            )\n'''
if text.count(old) != 1:
    raise SystemExit(f"expected one receipt Product lock block, found {text.count(old)}")
multi_path.write_text(text.replace(old, new, 1))

# Existing restock regression must identify the intended lock mode explicitly.
restock_test_path = Path("backend/tests/test_product_restock_concurrency_integrity.py")
text = restock_test_path.read_text()
text = text.replace(
    "If the production product lookup does not use ``FOR UPDATE``, both workers are",
    "If the production product lookup does not use ``FOR NO KEY UPDATE``, both workers are",
    1,
)
old = '''                    "FOR UPDATE" in normalized,\n'''
new = '''                    "FOR NO KEY UPDATE" in normalized,\n'''
if text.count(old) != 1:
    raise SystemExit(f"expected one restock lock detector, found {text.count(old)}")
restock_test_path.write_text(text.replace(old, new, 1))

# Cross-flow tests: Product locks must be NO KEY UPDATE; Stock remains FOR UPDATE.
purchase_test_path = Path("backend/tests/test_purchase_restock_lock_order_integrity.py")
text = purchase_test_path.read_text()
old = '''and "FROM PRODUCTS" in normalized\n            and "FOR UPDATE" in normalized'''
new = '''and "FROM PRODUCTS" in normalized\n            and "FOR NO KEY UPDATE" in normalized'''
count = text.count(old)
if count != 3:
    raise SystemExit(f"expected three Product lock detectors, found {count}")
purchase_test_path.write_text(text.replace(old, new))
