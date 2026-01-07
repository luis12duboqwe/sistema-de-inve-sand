from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool
from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
_is_sqlite_memory = settings.database_url in {"sqlite:///:memory:", "sqlite+pysqlite:///:memory:"}

_engine_kwargs: dict = {
    "connect_args": {"check_same_thread": False} if _is_sqlite else {},
    # pool_pre_ping es innecesario para :memory:
    "pool_pre_ping": not _is_sqlite_memory,
}

if _is_sqlite_memory:
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency that provides a database session.
    
    Yields a database session and ensures it is properly closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database tables.
    
    Creates all tables defined in models if they don't exist.
    """
    Base.metadata.create_all(bind=engine)

def check_db_connection():
    """
    Verify database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
