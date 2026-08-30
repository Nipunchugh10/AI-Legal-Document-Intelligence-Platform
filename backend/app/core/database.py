"""
Database Module
---------------
SQLAlchemy engine, session factory, and Base class for ORM models.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings

settings = get_settings()

# --- SQLAlchemy Engine ---
# Optimized connection pool configuration for high throughput & resilience (Day 43)
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,          # Persistent connection pool
    max_overflow=10,       # Extra connections during peak load
    pool_timeout=30,       # Timeout in seconds before raising pool exhaustion error
    pool_recycle=1800,     # Recycle connections every 30 minutes to prevent stale dropped sockets
    pool_pre_ping=True,    # Test connection liveness before checkout
    echo=settings.DEBUG,   # Log SQL statements in development
)

# --- Session Factory ---
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# --- Declarative Base ---
# All ORM models will inherit from this
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session per request.
    Ensures the session is properly closed after the request completes.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
