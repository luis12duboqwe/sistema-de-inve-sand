from pathlib import Path

path = Path("backend/tests/test_supplier_name_concurrency_integrity.py")
text = path.read_text()
old = r'"Proveedor\\u200bCentral"'
new = r'"Proveedor\u200bCentral"'
count = text.count(old)
if count != 2:
    raise SystemExit(f"expected two escaped U+200B fixtures, found {count}")
path.write_text(text.replace(old, new))
