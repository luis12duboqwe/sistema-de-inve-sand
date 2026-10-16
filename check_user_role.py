"""Safe read-only legacy user/role relationship aggregate (no usernames printed)."""
import sqlite3
from legacy_sqlite_diagnostics import open_legacy_snapshot


def main() -> int:
    with open_legacy_snapshot("Check user role relationships in an offline SQLite snapshot") as conn:
        try:
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            orphaned = conn.execute(
                "SELECT COUNT(*) FROM users u LEFT JOIN roles r ON u.role_id=r.id "
                "WHERE u.role_id IS NOT NULL AND r.id IS NULL"
            ).fetchone()[0]
        except sqlite3.Error as exc:
            print(f"Legacy user role schema FAILED: {exc}")
            return 1
    print(f"Legacy SQLite snapshot only: users={count}, missing_role_links={orphaned}")
    return 1 if orphaned else 0


if __name__ == "__main__":
    raise SystemExit(main())
