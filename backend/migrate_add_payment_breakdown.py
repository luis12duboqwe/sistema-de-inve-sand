"""Agrega desglose de pagos mixtos a órdenes."""

from sqlalchemy import create_engine, inspect, text

from app.config import settings


def main() -> None:
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("orders")}

    if "payment_breakdown" in columns:
        print("payment_breakdown ya existe en orders")
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE orders ADD COLUMN payment_breakdown TEXT"))
    print("Columna payment_breakdown agregada a orders")


if __name__ == "__main__":
    main()