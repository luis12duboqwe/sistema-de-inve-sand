"""Minimal offline order diagnostic; does NOT emit customer names or phones."""
import sqlite3
from legacy_sqlite_diagnostics import open_legacy_snapshot


def main() -> int:
    with open_legacy_snapshot("Inspect the latest order in an offline SQLite snapshot") as conn:
        try:
            order = conn.execute(
                "SELECT id, estado, total FROM orders ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if order is None:
                print("Legacy snapshot contains no orders")
                return 0
            lines = conn.execute(
                "SELECT COUNT(*) FROM order_items WHERE order_id = ?", (order[0],)
            ).fetchone()[0]
        except sqlite3.Error as exc:
            print(f"Legacy order schema FAILED: {exc}")
            return 1
    print(f"Legacy SQLite only: order_id={order[0]}, status={order[1]}, total={order[2]}, lines={lines}")
    print("No customer PII displayed; NOT the live PostgreSQL ledger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
