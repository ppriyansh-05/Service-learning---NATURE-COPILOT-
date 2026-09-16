"""
Database Session Management Module
Provides SQLAlchemy engine, sessionmaker, and database dependency for FastAPI routers.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Base class for SQLAlchemy ORM models
Base = declarative_base()

# SQLAlchemy Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# SessionFactory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI Dependency yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
