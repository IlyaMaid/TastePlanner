"""Minimal table stubs for legacy tables managed by hand-written SQL in
postgress/, needed only so SQLAlchemy can resolve foreign keys from
ORM-managed tables. Never diffed by Alembic autogenerate (see
alembic/env.py LEGACY_TABLES)."""

from sqlalchemy import BigInteger, Column, Table

from app.core.database import Base

recipes_stub = Table(
    "recipes",
    Base.metadata,
    Column("id", BigInteger, primary_key=True),
    extend_existing=True,
)
