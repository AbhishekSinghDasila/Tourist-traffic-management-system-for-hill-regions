"""
Database engine and session management.

Connection pooling is configured here once. Every request gets
its own session via the get_db() dependency, which always closes
the session after the request — even on error.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,        # base connections always open
    max_overflow=20,     # extra connections allowed under load
    pool_pre_ping=True,  # verify connection is alive before using it
    pool_recycle=3600,   # recycle connections every hour
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
