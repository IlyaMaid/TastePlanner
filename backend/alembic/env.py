from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.core.database import Base
from app.models import favorite, password_reset_token, profile, user  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# Tables managed by hand-written SQL in postgress/ that only appear here as
# minimal FK-target stubs (see app/models/_legacy_stubs.py). Never diffed.
LEGACY_TABLES = {"recipes"}


def include_object(object, name, type_, reflected, compare_to):
    """Ignore legacy tables that are managed by hand-written SQL in postgress/
    and are not (yet) fully declared as SQLAlchemy models, so autogenerate
    never proposes dropping or altering them."""
    if type_ == "table":
        if reflected and compare_to is None:
            return False
        if name in LEGACY_TABLES:
            return False
    if type_ in ("column", "index", "unique_constraint", "foreign_key_constraint"):
        table = getattr(object, "table", None)
        if table is not None and table.name in LEGACY_TABLES:
            return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
