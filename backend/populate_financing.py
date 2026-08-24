from app.database import SessionLocal
from app.models import Bank, FinancingOption
from app.utils.bank_names import bank_name_key, normalize_bank_name


def populate():
    db = SessionLocal()

    # Sample Banks
    banks_data = [
        {"name": "BAC Credomatic", "options": [
            {"months": 3, "rate": 0.04},
            {"months": 6, "rate": 0.07},
            {"months": 12, "rate": 0.12},
            {"months": 18, "rate": 0.18},
        ]},
        {"name": "Ficohsa", "options": [
            {"months": 3, "rate": 0.035},
            {"months": 6, "rate": 0.065},
            {"months": 12, "rate": 0.11},
            {"months": 24, "rate": 0.22},
        ]},
        {"name": "Promerica", "options": [
            {"months": 12, "rate": 0.10},
            {"months": 24, "rate": 0.20},
        ]},
    ]

    print("Populating banks...")
    try:
        for b_data in banks_data:
            name = normalize_bank_name(b_data["name"])
            normalized_key = bank_name_key(name)
            bank = db.query(Bank).filter(Bank.name_normalized == normalized_key).first()
            if not bank:
                bank = Bank(name=name, active=True)
                db.add(bank)
                db.flush()
                print(f"Created bank: {bank.name}")

                for opt in b_data["options"]:
                    option = FinancingOption(
                        bank_id=bank.id,
                        months=opt["months"],
                        rate=opt["rate"],
                        active=True,
                    )
                    db.add(option)
            else:
                print(f"Bank {bank.name} already exists")

        db.commit()
        print("Done!")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate()