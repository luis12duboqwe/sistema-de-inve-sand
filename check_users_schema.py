"""Read-only legacy SQLite schema diagnostic; never silently creates a database."""
from legacy_sqlite_diagnostics import open_legacy_snapshot


def main() -> int:
    with open_legacy_snapshot("Inspect the users table in an offline SQLite snapshot") as conn:
        fields = [row[1] for row in conn.execute("PRAGMA table_info(users)")]
    if not fields:
        print("Legacy SQLite users table not found")
        return 1
    print("Legacy users columns: " + ", ".join(fields))
    if "role_id" not in fields:
        print("Legacy schema is missing users.role_id")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
