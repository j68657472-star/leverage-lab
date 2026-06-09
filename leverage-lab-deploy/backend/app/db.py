"""Database setup. PostgreSQL in production, SQLite fallback for local dev."""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# DATABASE_URL example (Postgres):
#   postgresql+psycopg://user:pass@localhost:5432/etf_lab
# If unset, fall back to a local SQLite file so the app runs with zero config.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(os.path.dirname(__file__), "..", "etf_lab.db"),
)

# Managed Postgres providers (Render, Railway, Heroku, …) hand out URLs that
# start with "postgres://" or "postgresql://". SQLAlchemy + psycopg v3 needs the
# explicit "postgresql+psycopg://" driver prefix, so normalize it here. This
# means you can paste the provider's URL verbatim and it just works.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401 ensure models are registered

    Base.metadata.create_all(bind=engine)
