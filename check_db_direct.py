"""Read-only legacy SQLite check. Use --help for explicit snapshot flags."""
import sqlite3
from legacy_sqlite_diagnostics import open_legacy_snapshot


def main() -> int:
    with open_legacy_snapshot("Count tables in an offline legacy SQLite snapshot") as conn:
        try:
            products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        except sqlite3.Error as exc:
            print(f"Legacy SQLite schema check FAILED: {exc}")
            return 1
    print(f"Legacy SQLite snapshot only: products={products}, orders={orders}")
    print("Not a PostgreSQL production diagnostic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
