"""Check legacy AI schema using an explicit, read-only SQLite snapshot."""
from legacy_sqlite_diagnostics import open_legacy_snapshot


def main() -> int:
    with open_legacy_snapshot("Check AI tables in an offline legacy SQLite snapshot") as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        required = {"customers", "ai_profile_configs", "interaction_logs", "training_queue"}
        missing = sorted(required - tables)
        if missing:
            print("Legacy AI schema incomplete. Missing: " + ", ".join(missing))
            return 1
        cols = [row[1] for row in conn.execute("PRAGMA table_info(ai_profile_configs)")]
        print("Legacy AI tables found. ai_profile_configs columns: " + ", ".join(cols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
