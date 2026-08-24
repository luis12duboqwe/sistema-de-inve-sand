import threading

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Bank, User
from app.routers.financing import create_bank, update_bank
from app.schemas import BankCreate, BankUpdate
from app.utils.bank_names import bank_name_hash, bank_name_key
from postgres_test_utils import create_postgres_test_engine


def _actor() -> User:
    return User(
        username="finance-admin",
        email="finance-admin@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
    )


def _bank(name: str) -> Bank:
    return Bank(name=name, active=True, normal_card_rate=0)


def test_update_bank_rejects_duplicate_name_as_400(db_session):
    first = _bank("Banco Uno")
    second = _bank("Banco Dos")
    db_session.add_all([first, second])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_bank(
            second.id,
            BankUpdate(name="Banco Uno"),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "ya existe" in exc_info.value.detail
    db_session.refresh(second)
    assert second.name == "Banco Dos"


def test_create_bank_rejects_existing_name_as_400(db_session):
    db_session.add(_bank("Banco Existente"))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name="Banco Existente", active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert db_session.query(Bank).count() == 1


def test_create_bank_rejects_case_insensitive_trimmed_duplicate(db_session):
    db_session.add(_bank("Banco Uno"))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name="  banco uno  ", active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "ya existe" in exc_info.value.detail
    assert db_session.query(Bank).count() == 1


def test_update_bank_rejects_case_insensitive_trimmed_duplicate(db_session):
    first = _bank("Banco Uno")
    second = _bank("Banco Dos")
    db_session.add_all([first, second])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_bank(
            second.id,
            BankUpdate(name="  BANCO UNO  "),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    db_session.refresh(second)
    assert second.name == "Banco Dos"


def test_bank_name_normalization_handles_tabs_and_newlines(db_session):
    db_session.add(_bank("Banco Legacy"))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name="\tBANCO LEGACY\n", active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert db_session.query(Bank).count() == 1


def test_bank_name_normalization_rejects_canonically_equivalent_duplicate(db_session):
    composed = "Café Financiero"
    decomposed = "Cafe\u0301 Financiero"
    assert composed != decomposed
    assert bank_name_key(composed) == bank_name_key(decomposed)

    db_session.add(_bank(composed))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name=decomposed, active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert db_session.query(Bank).count() == 1


def test_compatibility_normalization_happens_before_casefold(db_session):
    compatibility_variant = "ᴮAC"
    ordinary_variant = "BAC"
    assert bank_name_key(compatibility_variant) == "bac"
    assert bank_name_key(compatibility_variant) == bank_name_key(ordinary_variant)

    db_session.add(_bank(compatibility_variant))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name=ordinary_variant, active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert db_session.query(Bank).count() == 1


def test_compatibility_normalization_strips_introduced_edge_whitespace(db_session):
    compatibility_variant = "´BAC"
    explicit_variant = " \u0301BAC"
    assert bank_name_key(compatibility_variant) == bank_name_key(explicit_variant)
    assert bank_name_hash(compatibility_variant) == bank_name_hash(explicit_variant)

    db_session.add(_bank(compatibility_variant))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name=explicit_variant, active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert db_session.query(Bank).count() == 1


def test_create_and_update_reject_blank_normalized_names(db_session):
    bank = _bank("Banco Inicial")
    db_session.add(bank)
    db_session.commit()

    with pytest.raises(HTTPException) as create_exc:
        create_bank(
            BankCreate(name="  ", active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )
    with pytest.raises(HTTPException) as update_exc:
        update_bank(
            bank.id,
            BankUpdate(name="  "),
            db=db_session,
            current_user=_actor(),
        )

    assert create_exc.value.status_code == 400
    assert update_exc.value.status_code == 400
    db_session.refresh(bank)
    assert bank.name == "Banco Inicial"


def test_create_bank_stores_trimmed_name_and_unique_key(db_session):
    response = create_bank(
        BankCreate(name="  Banco Nuevo  ", active=True, normal_card_rate=0),
        db=db_session,
        current_user=_actor(),
    )

    assert response.name == "Banco Nuevo"
    stored = db_session.get(Bank, response.id)
    assert stored is not None
    assert stored.name == "Banco Nuevo"
    assert stored.name_normalized == "banco nuevo"
    assert stored.name_key_hash == bank_name_hash("Banco Nuevo")
    assert len(stored.name_key_hash) == 64


def test_create_bank_allows_casefold_key_to_expand_beyond_255(db_session):
    display_name = "İ" * 128
    normalized_key = bank_name_key(display_name)
    assert len(display_name) == 128
    assert len(normalized_key) == 256

    response = create_bank(
        BankCreate(name=display_name, active=True, normal_card_rate=0),
        db=db_session,
        current_user=_actor(),
    )

    stored = db_session.get(Bank, response.id)
    assert stored is not None
    assert stored.name == display_name
    assert stored.name_normalized == normalized_key
    assert stored.name_key_hash == bank_name_hash(display_name)


def test_create_bank_handles_canonical_key_larger_than_postgres_btree_limit(db_session):
    # U+FDFA expands heavily under NFKC. The display name still fits the 255-char
    # API cap, but the full canonical key is >8 KB and must never be B-tree indexed.
    display_name = "ﷺ" * 255
    normalized_key = bank_name_key(display_name)
    assert len(display_name) == 255
    assert len(normalized_key.encode("utf-8")) > 8000

    response = create_bank(
        BankCreate(name=display_name, active=True, normal_card_rate=0),
        db=db_session,
        current_user=_actor(),
    )

    stored = db_session.get(Bank, response.id)
    assert stored is not None
    assert stored.name_normalized == normalized_key
    assert stored.name_key_hash == bank_name_hash(display_name)
    assert len(stored.name_key_hash) == 64


def test_update_bank_still_persists_valid_changes(db_session):
    bank = _bank("Banco Inicial")
    db_session.add(bank)
    db_session.commit()

    response = update_bank(
        bank.id,
        BankUpdate(name="  Banco Actualizado  ", active=False),
        db=db_session,
        current_user=_actor(),
    )

    assert response.name == "Banco Actualizado"
    assert response.active is False
    db_session.refresh(bank)
    assert bank.name == "Banco Actualizado"
    assert bank.name_normalized == "banco actualizado"
    assert bank.name_key_hash == bank_name_hash("Banco Actualizado")
    assert bank.active is False


def test_database_unique_key_blocks_concurrent_case_variants():
    engine, _, cleanup = create_postgres_test_engine("bank_name_uniqueness")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    barrier = threading.Barrier(2)
    results: list[str] = []
    results_lock = threading.Lock()

    def worker(name: str) -> None:
        session: Session = SessionLocal()
        try:
            session.add(_bank(name))
            barrier.wait()
            session.commit()
            result = "ok"
        except IntegrityError:
            session.rollback()
            result = "duplicate"
        finally:
            session.close()

        with results_lock:
            results.append(result)

    first = threading.Thread(target=worker, args=("BAC",))
    second = threading.Thread(target=worker, args=("  bac  ",))
    first.start()
    second.start()
    first.join()
    second.join()

    try:
        assert sorted(results) == ["duplicate", "ok"]
        check_session: Session = SessionLocal()
        try:
            rows = check_session.query(Bank).all()
            assert len(rows) == 1
            assert rows[0].name_normalized == "bac"
            assert rows[0].name_key_hash == bank_name_hash("BAC")
        finally:
            check_session.close()
    finally:
        cleanup()
