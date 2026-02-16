"""
SQLAlchemy database engine, session factory, and base model.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def get_engine():
    """Create a SQLAlchemy engine from settings."""
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,     # Recycle connections every 5 min
        echo=False,
    )


engine = get_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    """FastAPI dependency: yields a DB session, auto-closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables (for development / initial setup)."""
    Base.metadata.create_all(bind=engine)
