import pytest
from postgres_test_utils import assert_safe_test_database_url


@pytest.mark.parametrize("unsafe", [
    "postgresql+psycopg2://u:p@127.0.0.1:5432/inventory",
    "postgresql+psycopg2://u:p@live.example:5432/inventory_test",
    "sqlite:///inventory_test",
])
def test_postgres_unsafe_database_is_rejected(unsafe):
    with pytest.raises(RuntimeError, match="descartable"):
        assert_safe_test_database_url(unsafe)


def test_postgres_test_db_allows_local_ephemeral_database():
    assert_safe_test_database_url("postgresql+psycopg2://u:p@127.0.0.1:5432/inventory_test")
    assert_safe_test_database_url("postgresql+psycopg2://u:p@localhost:5432/inventory_e2e")
